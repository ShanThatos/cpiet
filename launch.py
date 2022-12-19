import sys

import src.compiler as compiler
import src.preprocess as preprocessor

def launch_main():
    start_file = sys.argv[1]
    source_code = preprocessor.preprocess(start_file)
    compiler.compile(source_code)
    print("Finished compiling")

if __name__ == "__main__":
    launch_main()
