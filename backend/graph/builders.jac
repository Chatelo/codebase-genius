#* Graph builder walkers for Codebase Genius.
# These walkers construct the Code Context Graph by creating nodes and edges.
*#

import from graph.nodes { Repository, Directory, CodeFile, Function, Class, Module }
import from graph.edges { Contains, Defines, Calls, Inherits, Imports }
import from utils.repo { clone_or_open_repo }
import from utils.fs_map { scan_repo_tree }
import from utils.ts_analyze { extract_entities }

#* Simple function to build a repository graph from file data *#
def build_repo_graph(
    root_node: any,
    repo_url: str,
    files: list,
    entities: dict
) -> any {
    # Create Repository node
    repo_node = root_node ++> Repository(url=repo_url);

    # Extract repository name from URL
    url_parts = repo_url.rstrip('/').split('/');
    repo_name = "";
    if len(url_parts) > 0 {
        repo_name = url_parts[-1];
    }
    repo_node.name = repo_name;

    # Track directories and files
    dir_nodes = {};
    file_nodes = {};

    # Create Directory and CodeFile nodes
    for file_info in files {
        file_path = "";
        if "path" in file_info { file_path = file_info["path"]; }

        # Extract directory path
        path_parts = file_path.split('/');
        current_parent = repo_node;

        # Build directory hierarchy
        if len(path_parts) > 1 {
            dir_path = "";
            i = 0;
            while i < len(path_parts) - 1 {
                if dir_path != "" { dir_path += "/"; }
                dir_path += path_parts[i];

                # Create directory node if not exists
                if dir_path not in dir_nodes {
                    dir_node = Directory(
                        path=dir_path,
                        name=path_parts[i]
                    );
                    current_parent ++> dir_node;
                    dir_nodes[dir_path] = dir_node;
                    current_parent = dir_node;
                } else {
                    current_parent = dir_nodes[dir_path];
                }
                i += 1;
            }
        }

        # Create CodeFile node
        lang = "";
        if "language" in file_info { lang = file_info["language"]; }
        sz = 0;
        if "size" in file_info { sz = file_info["size"]; }
        ln = 0;
        if "lines" in file_info { ln = file_info["lines"]; }

        file_node = CodeFile(
            path=file_path,
            language=lang,
            size=sz,
            lines=ln
        );
        current_parent ++> file_node;

        file_nodes[file_path] = file_node;

        # Mark test/example/doc files
        lower_path = file_path.lower();
        if "test" in lower_path or "spec" in lower_path {
            file_node.is_test = True;
        }
        if "example" in lower_path or "demo" in lower_path {
            file_node.is_example = True;
        }
        if lang == "markdown" or lang == "rst" or ".md" in lower_path or ".rst" in lower_path {
            file_node.is_doc = True;
        }
    }

    # Add Function and Class nodes from entities
    if "files" in entities {
        for file_ent in entities["files"] {
            file_path = "";
            if "file" in file_ent {
                # Extract relative path from absolute path
                abs_path = file_ent["file"];
                # Simple path extraction
                parts = abs_path.split('/');
                # Find the file name in our file_nodes
                for fp in file_nodes {
                    if fp in abs_path {
                        file_path = fp;
                        break;
                    }
                }
            }

            if file_path != "" and file_path in file_nodes {
                target_file = file_nodes[file_path];

                # Add Function nodes
                if "functions" in file_ent {
                    for func_name in file_ent["functions"] {
                        func_node = Function(name=func_name);
                        target_file ++> func_node;
                    }
                }

                # Add Class nodes
                if "classes" in file_ent {
                    for class_name in file_ent["classes"] {
                        class_node = Class(name=class_name);
                        target_file ++> class_node;
                    }
                }
            }
        }
    }

    return repo_node;
}

#* StatsCollector: Traverses the graph and computes statistics *#
walker StatsCollector {
    has stats: dict = {};
    
    can collect with Repository entry {
        # Initialize stats
        visitor.stats = {
            "files": 0,
            "code_files": 0,
            "docs": 0,
            "tests_files": 0,
            "examples_files": 0,
            "functions": 0,
            "classes": 0,
            "languages": {},
            "top_dirs": {}
        };
        
        # Traverse all CodeFile nodes
        visit [-->**](`?CodeFile);
        
        # Traverse all Function nodes
        visit [-->**](`?Function);
        
        # Traverse all Class nodes
        visit [-->**](`?Class);
        
        # Store stats in Repository node
        here.stats = visitor.stats;
        
        report visitor.stats;
    }
    
    can count_file with CodeFile entry {
        visitor.stats["files"] += 1;
        
        if here.language != "" and here.language != "unknown" {
            visitor.stats["code_files"] += 1;
            
            # Count by language
            if here.language not in visitor.stats["languages"] {
                visitor.stats["languages"][here.language] = 0;
            }
            visitor.stats["languages"][here.language] += 1;
        }
        
        if here.is_doc {
            visitor.stats["docs"] += 1;
        }
        
        if here.is_test {
            visitor.stats["tests_files"] += 1;
        }
        
        if here.is_example {
            visitor.stats["examples_files"] += 1;
        }
        
        # Count top-level directory
        path_parts = here.path.split('/');
        if len(path_parts) > 0 {
            top_dir = path_parts[0];
            if top_dir not in visitor.stats["top_dirs"] {
                visitor.stats["top_dirs"][top_dir] = 0;
            }
            visitor.stats["top_dirs"][top_dir] += 1;
        }
    }
    
    can count_function with Function entry {
        visitor.stats["functions"] += 1;
    }
    
    can count_class with Class entry {
        visitor.stats["classes"] += 1;
    }
}

#* DocCollector: Traverses the graph and collects documentation-relevant data *#
walker DocCollector {
    has top_n: int = 10;
    has top_files: list = [];
    has api_classes: list = [];
    has total_functions: int = 0;
    
    can collect with Repository entry {
        # Collect top files by lines
        all_files = here [-->**](`?CodeFile);
        
        # Sort by lines (manual bubble sort since we don't have sorted())
        file_list = [];
        for f in all_files {
            file_list.append({"path": f.path, "lines": f.lines, "size": f.size});
        }
        
        # Simple selection sort for top N
        i = 0;
        while i < len(file_list) and i < visitor.top_n {
            max_idx = i;
            j = i + 1;
            while j < len(file_list) {
                if file_list[j]["lines"] > file_list[max_idx]["lines"] {
                    max_idx = j;
                }
                j += 1;
            }
            # Swap
            if max_idx != i {
                temp = file_list[i];
                file_list[i] = file_list[max_idx];
                file_list[max_idx] = temp;
            }
            visitor.top_files.append(file_list[i]);
            i += 1;
        }
        
        # Collect API surface (classes and functions)
        all_classes = here [-->**](`?Class);
        for cls in all_classes {
            if len(visitor.api_classes) < visitor.top_n {
                visitor.api_classes.append(cls.name);
            }
        }
        
        all_functions = here [-->**](`?Function);
        visitor.total_functions = len(all_functions);
        
        report {
            "top_files": visitor.top_files,
            "api_classes": visitor.api_classes,
            "total_functions": visitor.total_functions
        };
    }
}

