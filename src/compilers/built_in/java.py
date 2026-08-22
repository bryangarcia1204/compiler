# src/compilers/builtin/java.py
import os
from typing import List, Tuple, Optional, Any, Dict
from ..base import CompilerStrategy


class JavaStrategy(CompilerStrategy):
    @property
    def tool_name(self) -> str:
        return 'java'

    @property
    def supported_extensions(self) -> List[str]:
        return ['.java']

    def build_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        output_type: str = 'exe',
        release_mode: bool = False,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        cmd = ['javac', file_path]
        post_actions = []
        if output_path and output_path.endswith('.jar'):
            class_dir = os.path.dirname(file_path)
            post_actions.append(('jar', output_path, class_dir))
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, post_actions

    def build_package_command(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        target: str = 'native'
    ) -> Tuple[List[str], Optional[str], List[Tuple[str, Any]]]:
        extra_args = extra_args or []
        jar_name = output_path or os.path.splitext(os.path.basename(file_path))[0] + '.jar'
        class_dir = os.path.dirname(file_path)
        cmd = ['jar', 'cf', jar_name, '-C', class_dir, '.']
        if extra_args:
            cmd.extend(extra_args)
        return cmd, None, []

    def generate_config_files(self, project_info: Dict, targets: List[str]) -> Dict[str, str]:
        """Genera archivos de configuración para Java."""
        project_name = os.path.basename(project_info.get('project_dir', 'mi_proyecto'))
        group_id = project_name.lower()
        files = {}
        files['pom.xml'] = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{group_id}</groupId>
    <artifactId>{project_name}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
    <dependencies>
        <!-- Añade aquí tus dependencias -->
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-jar-plugin</artifactId>
                <version>3.2.0</version>
                <configuration>
                    <archive>
                        <manifest>
                            <mainClass>{group_id}.{project_name}.Main</mainClass>
                        </manifest>
                    </archive>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
'''
        files['.gitignore'] = """*.class
*.jar
*.war
*.ear
target/
.idea/
*.iml
"""
        return files


STRATEGY_CLASS = JavaStrategy
