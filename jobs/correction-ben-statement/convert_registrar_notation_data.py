import csv


# Function to read CSV and convert to a Python array
def csv_to_python_array(file_path):
    array = []

    # Open the CSV file and read its contents
    with open(file_path, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            array.extend(row)  # Add each element from the row to the array

    return array


# Function to write the Python array to a file, with each element on a new row
def write_to_python_file(array, output_file):
    with open(output_file, 'w') as file:
        file.write('rn_businesses = [\n')  # Start the array in Python format
        for element in array:
            file.write(f"    '{element}',\n")  # Write each element in array
        file.write(']\n')  # End the array in Python format


input_csv = 'registrar_notation_result.csv'
output_python_file = 'rn_output.py'

# Convert CSV to Python array
python_array = csv_to_python_array(input_csv)

# Write the array to a Python file
write_to_python_file(python_array, output_python_file)

print(f"Python array has been written to {output_python_file}")
