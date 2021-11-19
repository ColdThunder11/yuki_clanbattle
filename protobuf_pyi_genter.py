# this file is only for project protobuf simple like this
from typing import Any


protobuf_file = "ws_protocol.proto"


output_file_name = protobuf_file[:-6] + "_pb2.pyi"


output_file = ""

output_file += "from typing import Any\n\n"

with open(protobuf_file, "r") as fp:
    lines = fp.readlines()
    line_count = 0
    while line_count < len(lines):
        if lines[line_count].startswith("message"):
            message_name = lines[line_count].split(" ")[1]
            output_file += f"class {message_name}:\n\n"
            line_count += 1
            while not lines[line_count].startswith("}"):
                line_str = lines[line_count].strip()
                var_type = line_str.split(" ")[0]
                var_name = line_str.split(" ")[1]
                if var_type == "string":
                    var_type = "str"
                elif var_type == "uint32":
                    var_type = "int"
                else:
                    var_type = "Any"
                output_file += f"    {var_name}: {var_type}\n"
                line_count += 1
            output_file += "\n    "
            output_file += f'''
    def __str__(self) -> str:
        ...

    def IsInitialized() -> bool:
        ...

    def CopyFrom(self, other_msg: {message_name}):
        ...

    def Clear(self):
        ...

    def SerializeToString(self) -> bytes:
        ...

    def ParseFromString(self, data: bytes) -> {message_name}:
        ...
            '''.strip()
            output_file += "\n\n"
        else:
            line_count += 1
            continue
    with open(output_file_name, "w") as fpo:
        fpo.write(output_file)
