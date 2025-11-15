def merge_csv_files(self, input_files: List[str], output_file: str, 
                        remove_duplicates: bool = True):
        
        all_rows = []
        headers = None
        
        for file in input_files:
            with open(file, 'r') as f:
                reader = csv.DictReader(f)
                if headers is None:
                    headers = reader.fieldnames
                all_rows.extend(list(reader))
        
        if remove_duplicates:
            seen = set()
            unique_rows = []
            for row in all_rows:
                row_tuple = tuple(sorted(row.items()))
                if row_tuple not in seen:
                    seen.add(row_tuple)
                    unique_rows.append(row)
            all_rows = unique_rows
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_rows)
        
        self.logger.info(f"Merged {len(input_files)} files into {output_file}")
        return len(all_rows)
    
