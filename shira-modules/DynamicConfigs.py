from dataclasses import dataclass, field, is_dataclass, fields
from datetime import datetime
from json import JSONEncoder
from pathlib import Path
from typing import Dict, Optional, Any, Type

import yaml


class DynamicDict:
    """Wrapper Class that makes dictionary accessible as objects"""
    def __init__(self, data: dict):
        self._data = {}
        for key, value in data.items():
            self._data[key] = self._convert_value(value)

    def _convert_value(self, value):
        """리스트 등에 nested 된 요소도 recursive하게 처리"""
        if isinstance(value, dict):
            # TranslatorService의 경우 처리
            if "__type__" in value and value["__type__"] == "TranslatorService":
                return TranslatorService.from_dict(value["value"])
            return DynamicDict(value)
        elif isinstance(value, list):
            # 리스트 내부 요소 변환
            return [self._convert_value(item) for item in value]
        else:
            return value
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        if name == '_data':
            super().__setattr__(name, value)
        else:
            if isinstance(value, dict):
                self._data[name] = DynamicDict(value)
            else:
                self._data[name] = value

    def __delattr__(self, name):
        if name in self._data:
            del self._data[name]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self._data[key] = DynamicDict(value)
        else:
            self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data
            
    def items(self):
        return self._data.items()
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data})"

    def clear(self):
        self._data.clear()

    def copy(self):
        return DynamicDict(self._data.copy())

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def popitem(self):
        return self._data.popitem()

    def setdefault(self, key, default=None):
        if key not in self._data:
            self._data[key] = self._convert_value(default)
        return self._data[key]

    def update(self, other=None, **kwargs):
        if other is not None:
            if isinstance(other, DynamicDict):
                other = other._data
            for key, value in other.items():
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def to_dict(self):
        result = {}
        for key, value in self._data.items():
            if isinstance(value, DynamicDict):
                result[key] = value.to_dict()
            elif isinstance(value, TranslatorService):
                result[key] = {
                    "__type__": "TranslatorService",
                    "value": value.to_dict()
                }
            else:
                result[key] = value
        return result

@dataclass
class DynamicDataclass:
    _dynamic_fields: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize any additional attributes after the dataclass is created"""
        if not hasattr(self, '_dynamic_fields'):
            self._dynamic_fields = {}

    def __getattr__(self, name):
        if name in [f.name for f in fields(self.__class__)]:
            return super().__getattribute__(name)
        if name in self._dynamic_fields:
            return self._dynamic_fields[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in [f.name for f in fields(self.__class__)]:
            if isinstance(value, dict):
                super().__setattr__(name, DynamicDict(value))
            else:
                super().__setattr__(name, value)
        else:
            if isinstance(value, dict):
                self._dynamic_fields[name] = DynamicDict(value)
            else:
                self._dynamic_fields[name] = value

def dataclass_to_dict(instance: Any) -> dict:
    """데이터클래스 인스턴스를 dictionary로 변환"""
    if not is_dataclass(instance):
        if isinstance(instance, DynamicDict):
            return instance.to_dict()
        elif isinstance(instance, TranslatorService):
            return {
                "__type__": "TranslatorService",
                "value": instance.to_dict()
            }
        return instance

    result = {}
    for field in fields(instance):
        value = getattr(instance, field.name)
        # _parent_translator 필드는 직렬화하지 않음
        if field.name in ['_parent_translator', '_dynamic_fields']:
            continue

        if isinstance(value, NowUsing):
            result[field.name] = value.to_dict()
        elif isinstance(value, DynamicDict):
            result[field.name] = dataclass_to_dict(value)
        elif isinstance(value, dict):
            result[field.name] = {k: dataclass_to_dict(v) for k, v in value.items()}
        elif isinstance(value, TranslatorService):
            result[field.name] = {
                "__type__": "TranslatorService",
                "value": value.to_dict()
            }
        elif is_dataclass(value):
            result[field.name] = dataclass_to_dict(value)
        elif isinstance(value, Path):
            result[field.name] = {
                "__type__": "Path",
                "value": value.absolute().as_posix()
            }
        else:
            result[field.name] = value

    if hasattr(instance, '_dynamic_fields'):
        for key, value in instance._dynamic_fields.items():
            if key != '_parent_translator':
                result[key] = dataclass_to_dict(value)

    return result

def dict_to_dataclass(data: Dict[str, Any], cls: Type) -> Any:
    """dictionary에서 데이터클래스 인스턴스 생성"""
    if not is_dataclass(cls):
        return data

    field_types = {f.name: f.type for f in fields(cls)}
    init_args = {}
    dynamic_fields = {}

    for key, value in data.items():
        if key in field_types:
            if isinstance(value, dict):
                if cls == NowUsing:
                    # NowUsing 클래스의 경우 category와 name을 내부 필드로 변환
                    if 'category' in value:
                        init_args['_service_category'] = value['category']
                    if 'name' in value:
                        init_args['_service_name'] = value['name']
                elif "__type__" in value:
                    if value["__type__"] == "TranslatorService":
                        init_args[key] = TranslatorService.from_dict(value["value"])
                    elif value["__type__"] == "Path":
                        init_args[key] = Path(value["value"])
                    else:
                        init_args[key] = value["value"]
                else:
                    field_type = field_types[key]
                    if field_type == APIBased:
                        init_args[key] = APIBased(value)
                    else:
                        init_args[key] = dict_to_dataclass(value, field_type)
            else:
                init_args[key] = value
        else:
            dynamic_fields[key] = value

    instance = cls(**init_args)
    for key, value in dynamic_fields.items():
        setattr(instance, key, value)
    return instance

@dataclass
class TranslatorService:
    """Flexible data classes for setting up translation services"""
    REQUIRED_FIELDS = {'service_name','key', 'request_form', 'client_type', 'base_url'}

    service_name: str = None
    key: str = None
    request_form: str = None
    client_type: str = None
    base_url: str = None
    _extra_fields: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 필수 필드 검증
        for field in self.REQUIRED_FIELDS:
            if not hasattr(self, field):
                raise ValueError(f"'{field}' field is required")
            
        # client_type별 추가 검증
        if self.client_type == 'openai':
            if 'model' not in self._extra_fields:
                raise ValueError("OpenAI client requires 'model' field")

    def __getattr__(self, name):
        if name in self._extra_fields:
            return self._extra_fields[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in self.REQUIRED_FIELDS or name == '_extra_fields':
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_extra_fields'):
                self._extra_fields = {}
            self._extra_fields[name] = value

    def to_dict(self) -> dict:
        """TranslatorService를 dictionary로 변환"""
        result = {field: getattr(self, field) for field in self.REQUIRED_FIELDS}
        result.update(self._extra_fields)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'TranslatorService':
        """dictionary에서 TranslatorService 인스턴스 생성"""
        required_fields = {field: data.get(field) for field in cls.REQUIRED_FIELDS}
        extra_fields = {k: v for k, v in data.items() if k not in cls.REQUIRED_FIELDS}
        return cls(**required_fields, _extra_fields=extra_fields)

class APIBased(DynamicDict):
    DEFAULT_SERVICES = {
        'DeepL': {
            'service_name': 'DeepL',
            'key': None,
            'request_form': 'placeholder',
            'client_type': 'rest',
            'base_url': 'https://api-free.deepl.com/v2/translate',
            'headers_template': {
                'Authorization': 'DeepL-Auth-Key {api_key}'
            },
            'data_template': {
                'target_lang': 'KO'
            }
        },
        'DeepSeek': {
            'service_name': 'DeepSeek',
            'key': None,
            'request_form': None,
            'client_type': 'openai',
            'base_url': 'https://api.deepseek.com',
            'model': 'deepseek-chat',
            'temperature': 1.2,
            'system_prompt': """
                Translate following texts to Korean. Answer in "Speaker: Text" format. 
                Don't compress conversations arbitrarily. The "Speaker: Text" pair I provide and the "Speaker: Text" pair in the response must match.""",
            'headers_template': {},
            'data_template': {}
        }
    }

    def __init__(self, data: dict = None):
        default_data = {}
        for service_name, service_config in self.DEFAULT_SERVICES.items():
            service = TranslatorService.from_dict(service_config)
            default_data[service_name] = service

        if data:
            default_data.update(data)

        super().__init__(default_data)

    def add_service(self, service_data: dict):
        """새로운 서비스를 동적으로 추가"""
        service = TranslatorService.from_dict(service_data)
        self[service.service_name] = service

    def remove_service(self, service_name: str):
        if service_name in self._data:
            del self._data[service_name]
        else:
            raise KeyError(f"Service '{service_name}' not found.")

@dataclass
class LLMSettings(DynamicDataclass):
    models: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NowUsing(DynamicDataclass):
    _service_category: Optional[str] = field(default='api_based')
    _service_name: Optional[str] = field(default='DeepSeek')
    _parent_translator: Optional['Translator'] = field(default=None, repr=False)

    def __post_init__(self):
        super().__post_init__()
        if self._service_category is None:
            self._service_category = 'api_based'
        if self._service_name is None:
            self._service_name = 'DeepSeek'

    @property
    def category(self) -> Optional[str]:
        return self._service_category

    @category.setter
    def category(self, value: Optional[str]):
        self._service_category = value

    @property
    def name(self) -> Optional[str]:
        return self._service_name

    @name.setter
    def name(self, value: Optional[str]):
        self._service_name = value

    def to_dict(self) -> dict:
        """NowUsing 인스턴스를 dictionary로 변환"""
        return {
            'category': self._service_category,
            'name': self._service_name
        }

    def __getattr__(self, name):
        if name in ['_service_category', '_service_name', '_parent_translator', '_dynamic_fields']:
            return super().__getattr__(name)

        if self._service_category is None or self._service_name is None:
            raise ValueError("Translation service not set. Please set category and name first.")

        service = None
        if self._service_category == 'api_based':
            if not hasattr(self, '_parent_translator') or self._parent_translator is None:
                raise ValueError("Parent translator reference not set")
            try:
                service = self._parent_translator.api_based[self._service_name]
            except KeyError:
                raise ValueError(f"Service '{self._service_name}' not found in api_based services")
        elif self._service_category == 'local_llm':
            if not hasattr(self, '_parent_translator') or self._parent_translator is None:
                raise ValueError("Parent translator reference not set")
            service = self._parent_translator.local_llm.models.get(self._service_name)
            if service is None:
                raise ValueError(f"Service '{self._service_name}' not found in local_llm services")
        else:
            raise ValueError(f"Invalid service category: {self._service_category}")

        return getattr(service, name)

    def __setattr__(self, name, value):
        if name in ['_service_category', '_service_name', '_parent_translator', '_dynamic_fields']:
            super().__setattr__(name, value)
        elif name == 'category':
            self._service_category = value
        elif name == 'name':
            self._service_name = value
        else:
            raise AttributeError(f"Cannot set attributes directly on NowUsing instance")


@dataclass
class Translator(DynamicDataclass):
    api_based: APIBased = field(default_factory=APIBased)
    local_llm: LLMSettings = field(default_factory=LLMSettings)
    now_using: NowUsing = field(default_factory=NowUsing)

    def __post_init__(self):
        super().__post_init__()
        # Set parent reference for now_using
        self.now_using._parent_translator = self

@dataclass
class Settings(DynamicDataclass):
    js_path: Optional[Path] = None
    js_scripts_path: Optional[Path] = None
    work_dir: Optional[Path] = None
    translator: Translator = field(default_factory=Translator)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path):
            return {
                "__type__": "Path",
                "value": obj.absolute().as_posix()
            }
        elif hasattr(obj, 'isoformat'):
            return {
                "__type__": "datetime",
                "value": obj.isoformat()
            }
        elif isinstance(obj, bytes):
            return obj.decode('utf-8')
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, TranslatorService):
            return {
                "__type__": "TranslatorService",
                "value": obj.to_dict()
            }
        try:
            return JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

class YAMLConfigHandler:
    @staticmethod
    def get_default_settings() -> dict:
        """기본 설정값 반환"""
        # Create default instances of dataclasses
        default_now_using = NowUsing()
        default_now_using._service_name = 'DeepSeek'
        default_now_using._service_category = 'api_based'

        translator = Translator(
            api_based=APIBased(),  # This already contains default services
            local_llm=LLMSettings(),
            now_using=default_now_using
        )

        settings = Settings(
            js_path=None,
            js_scripts_path=None,
            work_dir=None,
            translator=translator
        )

        # Convert to dict format
        return dataclass_to_dict(settings)

    @staticmethod
    def save_settings(settings_path: Path, settings) -> None:
        """설정을 YAML 파일로 저장"""
        settings_dict = dataclass_to_dict(settings)
        with open(settings_path, 'w', encoding='utf-8') as f:
            yaml.dump(settings_dict, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    @staticmethod
    def load_settings(settings_path: Path, settings_class) -> Any:
        """YAML 파일에서 설정 로드. 파일이 없으면 기본 설정으로 생성"""
        try:
            if not settings_path.exists():
                # 기본 설정으로 새 파일 생성
                default_settings = YAMLConfigHandler.get_default_settings()
                with open(settings_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_settings, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
                return dict_to_dataclass(default_settings, settings_class)

            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_dict = yaml.safe_load(f) or {}
                if not settings_dict:  # 파일은 있지만 비어있는 경우
                    settings_dict = YAMLConfigHandler.get_default_settings()
                    YAMLConfigHandler.save_settings(settings_path, dict_to_dataclass(settings_dict, settings_class))
                return dict_to_dataclass(settings_dict, settings_class)

        except Exception as e:
            raise ValueError(f"Error loading settings: {str(e)}")


# YAML 직렬화 custom representer
def path_representer(dumper, data):
    return dumper.represent_mapping(
        '!Path',
        {'value': data.absolute().as_posix()}
    )

def datetime_representer(dumper, data):
    return dumper.represent_mapping(
        '!datetime',
        {'value': data.isoformat()}
    )

def translator_service_representer(dumper, data):
    return dumper.represent_mapping(
        '!TranslatorService',
        {'value': data.to_dict()}
    )

# YAML 역직렬화를 위한 custom constructor
def path_constructor(loader, node):
    value = loader.construct_mapping(node)
    return Path(value['value'])

def datetime_constructor(loader, node):
    value = loader.construct_mapping(node)
    return datetime.fromisoformat(value['value'])

def translator_service_constructor(loader, node):
    value = loader.construct_mapping(node)
    return TranslatorService.from_dict(value['value'])

# YAML에 custom 타입 등록
yaml.add_representer(Path, path_representer)
yaml.add_representer(datetime, datetime_representer)
yaml.add_representer(TranslatorService, translator_service_representer)

yaml.add_constructor('!Path', path_constructor)
yaml.add_constructor('!datetime', datetime_constructor)
yaml.add_constructor('!TranslatorService', translator_service_constructor)