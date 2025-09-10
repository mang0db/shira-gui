import json
import logging
import shutil
from http.cookiejar import LoadError as CookieLoadError
from pathlib import Path

import click

from .downloader import Dl
from .metadata_parser import TIGER_SINGLE, smart_metadata
from .musicbrainz_api import musicbrainz_enrich_tags
from .metadata_tagger import get_cover_local, metadata_applier

logging.basicConfig(
	format="[%(levelname)-8s %(asctime)s] %(message)s",
	datefmt="%H:%M:%S",
)

EXCLUDED_PARAMS = ("urls", "config_location", "url_txt", "no_config_file", "version", "help")


def write_default_config_file(ctx: click.Context):
	ctx.params["config_location"].parent.mkdir(parents=True, exist_ok=True)
	config_file = {param.name: param.default for param in ctx.command.params if param.name not in EXCLUDED_PARAMS}
	with open(ctx.params["config_location"], "w") as f:
		f.write(json.dumps(config_file, indent=4))


def no_config_callback(ctx: click.Context, param: click.Parameter, no_config_file: bool):
	if no_config_file:
		return ctx
	if not ctx.params["config_location"].exists():
		write_default_config_file(ctx)
	with open(ctx.params["config_location"], "r") as f:
		config_file = dict(json.load(f))
	for param in ctx.command.params:
		if config_file.get(param.name) is not None and ctx.get_parameter_source(param.name) != click.core.ParameterSource.COMMANDLINE: # type: ignore
			ctx.params[param.name] = param.type_cast_value(ctx, config_file[param.name]) # type: ignore
	return ctx


@click.command()
@click.argument("urls", nargs=-1, type=str, required=True)
@click.option("--final-path", "-f", type=Path, default="./YouTube Music", help="Path where the downloaded files will be saved.")
@click.option("--temp-path", "-t", type=Path, default="./temp", help="Path where the temporary files will be saved.")
@click.option("--cookies-location", "-c", type=Path, default=None, help="Location of the cookies file.")
@click.option("--ffmpeg-location", type=Path, default="ffmpeg", help="Location of the FFmpeg binary.")
@click.option("--config-location", type=Path, default=Path.home() / ".shiradl" / "config.json", help="Location of the config file.")
@click.option("--itag", "-i", type=str, default="140", help="Itag (audio quality).")
@click.option("--cover-size", type=click.IntRange(0, 16383), default=1200, help="Size of the cover.")
@click.option("--cover-format", type=click.Choice(["jpg", "png"]), default="jpg", help="Format of the cover.")
@click.option("--cover-quality", type=click.IntRange(1, 100), default=94, help="JPEG quality of the cover.")
@click.option("--cover-img", type=Path, default=None, help="Path to image or folder of images named video/song id")
@click.option("--cover-crop", type=click.Choice(["auto", "crop", "pad"]), default="auto", help="'crop' takes a 1:1 square from the center, pad always pads top & bottom")
@click.option("--template-folder", type=str, default="{albumartist}/{album}", help="Template of the album folders as a format string.")
@click.option("--template-file", type=str, default="{track:02d} {title}", help="Template of the song files as a format string.")
@click.option("--exclude-tags", "-e", type=str, default=None, help="List of tags to exclude from file tagging separated by commas without spaces.")
@click.option("--truncate", type=int, default=60, help="Maximum length of the file/folder names.")
@click.option("--log-level", "-l", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), default="INFO", help="Log level.")
@click.option("--save-cover", "-s", is_flag=True, help="Save cover as a separate file.")
@click.option("--overwrite", "-o", is_flag=True, help="Overwrite existing files.")
@click.option("--print-exceptions", "-p", is_flag=True, help="Print exceptions.")
@click.option("--url-txt", "-u", is_flag=True, help="Read URLs as location of text files containing URLs.")
@click.option("--no-config-file", "-n", is_flag=True, callback=no_config_callback, help="Don't use the config file.")
@click.option("--single-folder", "-w", is_flag=True, help="Wrap singles in their own folder instead of placing them directly into artist's folder.")
@click.option("--use-playlist-name", type=bool, is_flag=True, help="Uses the playlist name in the final location when downloading a playlist.")
@click.help_option("-h", "--help")
def cli(
	urls: tuple[str, ...],
	final_path: Path,
	temp_path: Path,
	cookies_location: Path,
	ffmpeg_location: Path,
	config_location: Path,
	itag: str,
	cover_size: int,
	cover_format: str,
	cover_quality: int,
	cover_img: Path,
	cover_crop: str,
	template_folder: str,
	template_file: str,
	exclude_tags: str,
	truncate: int,
	log_level: str,
	save_cover: bool,
	overwrite: bool,
	print_exceptions: bool,
	url_txt: bool,
	no_config_file: bool,
	single_folder: bool,
	use_playlist_name: bool
):
	logger = logging.getLogger(__name__)
	logger.setLevel(log_level)
	if not shutil.which(str(ffmpeg_location)):
		logger.critical(f'FFmpeg not found at "{ffmpeg_location}"')
		return
	if cookies_location is not None and not cookies_location.exists():
		logger.critical(f'Cookies file not found at "{cookies_location}"')
		return
	if url_txt:
		logger.debug("Reading URLs from text files")
		_urls = []
		for url in urls:
			with open(url, "r") as f:
				_urls.extend(f.read().splitlines())
		urls = tuple(_urls)
	logger.debug("Starting downloader")

	dl = Dl(
		final_path, 
		temp_path, 
		cookies_location, 
		ffmpeg_location, 
		itag, cover_size, 
		cover_format, 
		cover_quality, 
		template_folder, 
		template_file, 
		exclude_tags, 
		truncate, 
		dump_json=log_level == "DEBUG",
		use_playlist_name=use_playlist_name
	)
	download_queue = []
	for i, url in enumerate(urls):
		try:
			logger.debug(f'Checking "{url}" (URL {i + 1}/{len(urls)})')
			download_queue.append(dl.get_download_queue(url))
		except (CookieLoadError) as he: # handled exceptions
			logger.error(he, exc_info=False)
		except Exception:
			logger.error(f"Failed to check URL {i + 1}/{len(urls)}", exc_info=print_exceptions)
			logging.exception("")
	error_count = 0
	for i, url in enumerate(download_queue):
		for j, track in enumerate(url):
			logger.info(f'Downloading "{track["title"]}" (track {j + 1}/{len(url)} from URL {i + 1}/{len(download_queue)})')
			try:
				logger.debug("Getting tags")
				ytmusic_watch_playlist = dl.get_ytmusic_watch_playlist(track["id"])

				dl.tags = None
				tags = None
				is_single = False
				if ytmusic_watch_playlist is None:
					logger.info("No results on YTMusic API, using Tigerv2 to extract metadata")
					tag_track = track
					if "webpage_url_domain" not in track:
						tag_track = dl.get_ydl_extract_info(track["url"])
					logger.debug("Starting Tigerv2")
					tags = smart_metadata(tag_track, temp_path, "JPEG" if dl.cover_format == "jpg" else "PNG", cover_crop)
					is_single = tags.get("comments") == TIGER_SINGLE
					if is_single:
						tags["comments"] = str(track.get("webpage_url") or track.get("original_url") or track.get("url") or url)
				else:
					tags = dl.get_tags(ytmusic_watch_playlist, track)
					is_single = tags["tracktotal"] == 1
				logger.debug("Tags applied, fetching MusicBrainz Database")
				tags = musicbrainz_enrich_tags(tags, dl.soundcloud, dl.exclude_tags)
				# pprint(tags)
				logger.debug("Applied MusicBrainz Tags")
				if cover_img:
					local_img_bytes = get_cover_local(cover_img, track["url"] if dl.soundcloud else track["id"], dl.soundcloud)
					if local_img_bytes is not None:
						tags["cover_bytes"] = local_img_bytes
				logger.debug("Applied cover Image")
				final_location = dl.get_final_location(tags, ".mp3" if dl.soundcloud is True else ".m4a", is_single, single_folder)
				logger.debug(f'Final location is "{final_location}"')
				temp_location = dl.get_temp_location(track["id"])	
				if not final_location.exists() or overwrite:
					logger.debug(f'Downloading to "{temp_location}"')
					if dl.soundcloud is False:
						dl.download(track["id"], temp_location)
					else:
						dl.download_souncloud(track.get("original_url") or track["webpage_url"], temp_location)
					
					fixed_location = dl.get_fixed_location(track["id"])
					logger.debug(f'Remuxing to "{fixed_location}"')
					dl.fixup(temp_location, fixed_location)
					logger.debug("Applying tags")
					metadata_applier(tags, fixed_location, dl.exclude_tags)
					# if dl.soundcloud is False:
					# 	tagger_m4a(tags, fixed_location, dl.exclude_tags, dl.cover_format)
					# else:
					# 	tagger_mp3(tags, fixed_location, dl.exclude_tags, dl.cover_format)
					logger.debug("Moving to final location")
					dl.move_to_final_location(fixed_location, final_location)
				else:
					logger.warning("File already exists at final location, skipping")
				if save_cover:
					cover_location = dl.get_cover_location(final_location)
					if not cover_location.exists() or overwrite:
						logger.debug(f'Saving cover to "{cover_location}"')
						dl.save_cover(tags, cover_location)
					else:
						logger.debug(f'File already exists at "{cover_location}", skipping')
			except Exception:
				error_count += 1
				logger.error(
					f'Failed to download "{track["title"]}" (track {j + 1}/{len(url)} from URL ' + f"{i + 1}/{len(download_queue)})",
					exc_info=print_exceptions,
				)
				logging.exception("")
			finally:
				if temp_path.exists():
					logger.debug(f'Cleaning up "{temp_path}"')
					dl.cleanup()
	logger.info(f"Done ({error_count} error(s))")

