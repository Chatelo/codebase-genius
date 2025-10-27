#* Edge definitions for Codebase Genius graph architecture.
# Edges represent relationships between nodes and can carry metadata.
*#

#* Contains edge: Repository/Directory contains Directory/CodeFile *#
edge Contains {
    has depth: int = 0;
}

#* Defines edge: CodeFile defines Function/Class *#
edge Defines {
    has line_number: int = 0;
}

#* Calls edge: Function calls another Function *#
edge Calls {
    has frequency: int = 1;
    has line_number: int = 0;
    has call_type: str = "direct";  # direct, indirect, async
}

#* Inherits edge: Class inherits from another Class *#
edge Inherits {
    has inheritance_type: str = "extends";  # extends, implements, mixin
}

#* Imports edge: Module imports another Module *#
edge Imports {
    has import_type: str = "import";  # import, from_import, dynamic
    has alias: str = "";
}

#* References edge: Generic reference between any nodes *#
edge References {
    has reference_type: str = "";
    has context: str = "";
}

