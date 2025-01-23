import math

def power_of_two(value):
    # Add 1 to value to get the actual power of 2
    power_of_two = value + 1

    # Find the number of bits needed to represent this number
    # This effectively gives us 'n' where 2^n = power_of_two
    result = math.ceil(math.log2(power_of_two))

    # Return 'n' which is the next greatest power of 2
    return result


def read_pnm(file_path):
    with open(file_path, 'rb') as f:
        # Read header
        magic_number = f.readline().decode().strip()
        if magic_number not in ['P3']:
            raise ValueError("Invalid PNM format")

        # Parse width, height, and max grey value if applicable
        width, height = map(int, f.readline().decode().split())
        max_value = None
        if magic_number in ['P3']:
            max_value = int(f.readline().decode())

        bit_depth = power_of_two(max_value)

        # Read image data
        data = []
        # ASCII formats
        if magic_number in ['P3']:
            for line in f:
                # Combine three numbers into one
                values = [int(x) for x in line.decode().split()] # list of three numbers (e.g. RGB)
                pixel = (values[0] << (2*bit_depth)) | (values[1] << bit_depth) | values[2]
                data.append(pixel)
        else:
            for line in f:
                data.extend([int(x) for x in line.decode().split()])

        return (data, width, height, max_value)



def write_pnm(data, width, height, max_value, file_path, format):
    if format not in ['P3']:
        raise ValueError("Unsupported PNM format. Use 'P3' for ASCII")

    bit_depth = power_of_two(max_value)

    _data = []
    for value in data:
        # Split one number into three (e.g. RGB)
        _data.append(value >> (2*bit_depth))
        _data.append(value >> bit_depth & max_value)
        _data.append(value & max_value)

    with open(file_path, 'w') as f:
        # Write header
        f.write(f"{format}\n")
        f.write(f"{width} {height}\n")
        f.write(f"{max_value}\n")

        if format == 'P3':  # ASCII format
            for idx,value in enumerate(_data, 1):
                f.write(f"{value} ")
                if idx % 3 == 0: # 3 color components!
                    f.write("\n")
