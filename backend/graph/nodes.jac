#* Node definitions for Codebase Genius graph architecture.
# Nodes are passive data containers. Walkers contain the logic.
*#

#* Repository node: root of the code context graph *#
node Repository {
    has url: str;
    has name: str = "";
    has description: str = "";
    has readme_content: str = "";
    has summary: str = "";
    has documentation: str = "";
    has file_tree: list = [];
    has stats: dict = {};
    has error: str = "";

    # CCG relationship caches for typed edge materialization
    has ccg_calls: list = [];
    has ccg_inherits: list = [];
    has ccg_imports: list = [];
    has ccg_stats: dict = {};
}

#* Directory node: represents a folder in the repository *#
node Directory {
    has path: str;
    has name: str;
    has file_count: int = 0;
    has code_file_count: int = 0;
}

#* CodeFile node: represents a source code or documentation file *#
node CodeFile {
    has path: str;
    has language: str = "";
    has content: str = "";
    has size: int = 0;
    has lines: int = 0;
    has is_test: bool = False;
    has is_example: bool = False;
    has is_doc: bool = False;

}

#* Function node: represents a function or method *#
node Function {
    has name: str;
    has params: list = [];
    has return_type: str = "";
    has line_start: int = 0;
    has line_end: int = 0;
    has docstring: str = "";
    has is_async: bool = False;
    has is_method: bool = False;
}

#* Class node: represents a class definition *#
node Class {
    has name: str;
    has line_start: int = 0;
    has line_end: int = 0;
    has docstring: str = "";
    has methods: list = [];
    has properties: list = [];
    has is_abstract: bool = False;
}

#* Module node: represents an import/module reference *#
node Module {
    has name: str;
    has import_path: str = "";
    has is_external: bool = False;
}

