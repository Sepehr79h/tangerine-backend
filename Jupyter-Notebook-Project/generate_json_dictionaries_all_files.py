import os
import sys
import time
from tqdm import tqdm

directory_in_str = sys.argv[1]
directory = os.fsencode(directory_in_str)
num_python_files = 0

start_time = time.time()
for file in tqdm(os.listdir(directory)):
    filename = os.fsdecode(file)
    if filename.endswith("_no_comments.py"):
        num_python_files += 1
        full_path = os.path.join(directory_in_str, filename)
        json_filename = os.path.splitext(full_path)[0] + ".json"
        # fix filename with blank space
        filename = filename.replace(' ', '\ ')
        #breakpoint()
        command = f"pyright --outputjson {full_path} > {json_filename}"
        #command = f"pyright --outputjson --lib --project {full_path} > {json_filename}"
        #command = "pyright " + directory_in_str + filename
        #command = "/Users/cindyjiang/Desktop/pyright/packages/pyright/index.js --lib " + directory_in_str + filename
        #breakpoint()
        os.system(command)
        print("File {} has been analyzed and saved to {}.".format(filename, json_filename))
        #breakpoint()
end_time = time.time()

print("Total number of python files analyzed = {}!".format(num_python_files))
print("Time used = {} s!".format(end_time - start_time))