from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class MyFileReadToolSchema(BaseModel):
    """Input for MyFileReadTool."""

    file_path: str = Field(..., description="Mandatory file full path to read the file")
    start_line: int | None = Field(
        1, description="Line number to start reading from (1-indexed)"
    )
    line_count: int | None = Field(
        None, description="Number of lines to read. If None, reads the entire file"
    )
    encoding: str | None = Field(
        None, description="Text encoding to use when reading the file (e.g., 'utf-8', 'gbk', 'latin-1'). If None, uses the system default encoding."
    )


class MyFileReadTool(BaseTool):
    """A tool for reading file contents.

    This tool inherits its schema handling from BaseTool to avoid recursive schema
    definition issues. The args_schema is set to MyFileReadToolSchema which defines
    the required file_path parameter. The schema should not be overridden in the
    constructor as it would break the inheritance chain and cause infinite loops.

    The tool supports two ways of specifying the file path:
    1. At construction time via the file_path parameter
    2. At runtime via the file_path parameter in the tool's input

    Args:
        file_path (Optional[str]): Path to the file to be read. If provided,
            this becomes the default file path for the tool.
        **kwargs: Additional keyword arguments passed to BaseTool.

    Example:
        >>> tool = MyFileReadTool(file_path="/path/to/file.txt")
        >>> content = tool.run()  # Reads /path/to/file.txt
        >>> content = tool.run(file_path="/path/to/other.txt")  # Reads other.txt
        >>> content = tool.run(
        ...     file_path="/path/to/file.txt", start_line=100, line_count=50
        ... )  # Reads lines 100-149
    """

    name: str = "Read a file's content"
    description: str = "A tool that reads the content of a file. To use this tool, provide a 'file_path' parameter with the path to the file you want to read. Optionally, provide 'start_line' to start reading from a specific line, 'line_count' to limit the number of lines read, and 'encoding' to specify the text encoding."
    args_schema: type[BaseModel] = MyFileReadToolSchema
    file_path: str | None = None
    encoding: str | None = None

    def __init__(self, file_path: str | None = None, encoding: str | None = None, **kwargs: Any) -> None:
        """Initialize the MyFileReadTool.

        Args:
            file_path (Optional[str]): Path to the file to be read. If provided,
                this becomes the default file path for the tool.
            encoding (Optional[str]): Text encoding to use when reading the file
                (e.g., 'utf-8', 'gbk', 'latin-1'). If None, uses the system default.
            **kwargs: Additional keyword arguments passed to BaseTool.
        """
        if file_path is not None:
            kwargs["description"] = (
                f"A tool that reads file content. The default file is {file_path}, but you can provide a different 'file_path' parameter to read another file. You can also specify 'start_line', 'line_count', and 'encoding' to read specific parts of the file with custom encoding."
            )

        super().__init__(**kwargs)
        self.file_path = file_path
        self.encoding = encoding

    def _run(
        self,
        file_path: str | None = None,
        start_line: int | None = 1,
        line_count: int | None = None,
        encoding: str | None = None,
    ) -> str:
        file_path = file_path or self.file_path
        # 确保参数类型正确（LLM 可能传入字符串类型的数字）
        start_line = int(start_line) if start_line is not None else 1
        line_count = int(line_count) if line_count is not None and not "None" else None
        encoding = encoding or self.encoding

        if file_path is None:
            return "Error: No file path provided. Please provide a file path either in the constructor or as an argument."

        try:
            with open(file_path, "r", encoding=encoding) as file:
                if start_line == 1 and line_count is None:
                    return file.read()

                start_idx = max(start_line - 1, 0)

                selected_lines = [
                    line
                    for i, line in enumerate(file)
                    if i >= start_idx
                    and (line_count is None or i < start_idx + line_count)
                ]

                if not selected_lines and start_idx > 0:
                    return f"Error: Start line {start_line} exceeds the number of lines in the file."

                return "".join(selected_lines)
        except FileNotFoundError:
            return f"Error: File not found at path: {file_path}"
        except PermissionError:
            return f"Error: Permission denied when trying to read file: {file_path}"
        except Exception as e:
            return f"Error: Failed to read file {file_path}. {e!s}"
