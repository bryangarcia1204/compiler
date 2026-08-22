import os
from pathlib import Path
from ..utils import logger

log = logger.Logger()


class LanguageDetector:
    LANGUAGE_MAP = {
        '.c': {
            'name': 'C',
            'type': 'compiler',
            'default_outputs': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']
        },
        '.cpp': {
            'name': 'C++',
            'type': 'compiler',
            'default_outputs': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']
        },
        '.cc': {
            'name': 'C++',
            'type': 'compiler',
            'default_outputs': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']
        },
        '.cxx': {
            'name': 'C++',
            'type': 'compiler',
            'default_outputs': ['exe', 'bin', 'dll', 'so', 'dylib', 'a', 'lib', 'obj', 'pyd', 'wasm']
        },
        '.java': {
            'name': 'Java',
            'type': 'compiler',
            'default_outputs': ['class', 'jar', 'jar-exec', 'war', 'ear', 'aar', 'apk']
        },
        '.py': {
            'name': 'Python',
            'type': 'interpreter',
            'default_outputs': ['exe', 'bin', 'pyd', 'whl', 'sdist', 'egg']
        },
        '.js': {
            'name': 'JavaScript',
            'type': 'interpreter',
            'default_outputs': ['nodebin', 'nodepkg', 'exe']
        },
        '.rb': {
            'name': 'Ruby',
            'type': 'interpreter',
            'default_outputs': ['gem']
        },
        '.go': {
            'name': 'Go',
            'type': 'compiler',
            'default_outputs': ['go-bin', 'exe', 'bin', 'dll', 'so']
        },
        '.rs': {
            'name': 'Rust',
            'type': 'compiler',
            'default_outputs': ['rust-bin', 'cargo-release', 'exe', 'bin', 'dll', 'so', 'wasm']
        },
        '.cs': {
            'name': 'C#',
            'type': 'compiler',
            'default_outputs': ['dotnet', 'exe', 'dll', 'nupkg']
        },
        '.swift': {
            'name': 'Swift',
            'type': 'compiler',
            'default_outputs': ['exe', 'framework', 'pkg']
        },
        '.php': {
            'name': 'PHP',
            'type': 'interpreter',
            'default_outputs': ['phppkg']
        }
    }

    @classmethod
    def detect(cls, file_path: Path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in cls.LANGUAGE_MAP:
            info = cls.LANGUAGE_MAP[ext]
            result = {
                'extension': ext,
                'language': info['name'],
                'type': info['type'],
                'allowed_outputs': info.get('default_outputs', [])
            }
            log.debug(f"[LanguageDetector] Se ha detectado: {result}")
            return result
        return None

    @classmethod
    def is_compiled(cls, file_path: Path):
        info = cls.detect(file_path)
        return info and info['type'] == 'compiler'

    @classmethod
    def is_interpreted(cls, file_path: Path):
        info = cls.detect(file_path)
        return info and info['type'] == 'interpreter'
