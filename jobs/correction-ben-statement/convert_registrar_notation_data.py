import openpyxl


# Function to read Excel sheet and convert to a Python array
def excel_to_python_array(file_path, sheet_name):
    array = []

    # Load the workbook and select the sheet
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook[sheet_name]

    # Iterate through rows and columns to extract data
    for row in sheet.iter_rows(values_only=True):
        for cell in row:
            if cell is not None:  # Skip empty cells
                array.append(cell)

    return array


input_csv = 'data.xlsx'
output_python_file = 'rn_output.py'


# Function to write the Python array to a file, with each element on a new row
def write_to_python_file(array, output_file):
    with open(output_file, 'w') as file:
        file.write('businesses = [\n')  # Start the array in Python format
        for element in array:
            file.write(f"    '{element}',\n")  # Write each element in array
        file.write(']\n')  # End the array in Python format


python_array = excel_to_python_array(input_csv, 'Sheet1')

# Write the array to a Python file
write_to_python_file(python_array, output_python_file)

print(f"Python array has been written to {output_python_file}")
