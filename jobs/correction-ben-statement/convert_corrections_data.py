import pandas as pd


# Function to convert CSV to array of arrays using pandas
def convert_csv_to_array_of_arrays(csv_filename):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_filename)

    # Convert the DataFrame to a list of lists (array of arrays)
    rows_array = df.values.tolist()
    return rows_array


# Write the array of arrays to a Python file
def write_array_to_python_file(array, output_filename):   
    with open(output_filename, 'w') as f:
        f.write('correction_businesses = [\n')  # Start the Python array
        for row in rows_array:
            f.write(f'    {row},\n')  # Write each row as a list
        f.write(']\n')  # End the Python array


# Specify your input and output filenames
csv_filename = 'corrections_results.csv'
output_filename = 'corrections_output.py'

# Convert CSV to array of arrays
rows_array = convert_csv_to_array_of_arrays(csv_filename)

# Write the result to a Python file
write_array_to_python_file(rows_array, output_filename)

print(f"Data has been written to {output_filename}")
