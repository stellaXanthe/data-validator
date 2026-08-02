import argparse
from validator.connectors.file_connector import FileConnector
from validator.matcher import match_fields
from validator.schema import compare_schemas
from validator.comparator import compare_data
from validator.report import print_report


def main():
    parser = argparse.ArgumentParser(description="Validate data flow from source to target.")
    parser.add_argument("--source", required=True, help="Path to source file (CSV/Parquet/JSON)")
    parser.add_argument("--target", required=True, help="Path to target file (CSV/Parquet/JSON)")
    parser.add_argument("--keys", required=True, help="Comma-separated key column(s), e.g. 'id' or 'id,region'")
    args = parser.parse_args()

    connector = FileConnector()

    source_schema = connector.get_schema(args.source)
    target_schema = connector.get_schema(args.target)

    field_map = match_fields(source_schema, target_schema)
    print(f"Field mapping: {field_map}\n")

    schema_diff = compare_schemas(source_schema, target_schema, field_map)
    if schema_diff.missing_in_target or schema_diff.missing_in_source or schema_diff.type_mismatches:
        print("Schema differences detected:")
        if schema_diff.missing_in_target:
            print(f"  Columns only in source: {schema_diff.missing_in_target}")
        if schema_diff.missing_in_source:
            print(f"  Columns only in target: {schema_diff.missing_in_source}")
        if schema_diff.type_mismatches:
            print(f"  Type mismatches: {schema_diff.type_mismatches}")
        print()

    source_df = connector.read_data(args.source)
    target_df = connector.read_data(args.target)

    key_columns = args.keys.split(",")
    result = compare_data(source_df, target_df, field_map, key_columns)

    print_report(result)


if __name__ == "__main__":
    main()