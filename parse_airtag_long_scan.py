#!/usr/bin/env python3
import pandas as pd
import re

filepath="airtag_out.txt"
fields = ['timestamp', 'packet_num', 'channel_num', 'access_addr', 'adv_pdu', 'tx', 'rx', 'payload_length', 'advertising_addr', 'data', 'crc']
num_fields = len(fields)
field_junk_regex = ["us", "Pkt", "Ch", "AA:", "ADV_PDU_t((\d)+):", "T", "R", "PloadL", "AdvA:", "Data:", "CRC"]
outfile="airtag_long_scan.csv"

def remove_data_labels(raw):
    clean = raw

    for i, row in raw.iterrows():
        for j in range(num_fields):
            #print("row "+ str(i))
            raw_str = str(raw.at[i, fields[j]])
            pattern = field_junk_regex[j]

            #print(raw_str)
            #print(pattern)
            
            clean.at[i, fields[j]] = re.sub(pattern, '', raw_str)
    
    return clean

def main():
    ble_msgs_raw = pd.read_csv(filepath, names=fields, delimiter=' ', skiprows=6, on_bad_lines='skip')

    total_raw_records  = len(ble_msgs_raw)
    print(total_raw_records)
    ble_msgs_raw = ble_msgs_raw.drop(range((total_raw_records - 3), total_raw_records))

    ble_msgs = remove_data_labels(ble_msgs_raw)

    #print(ble_msgs.iloc[0])

    total_records = len(ble_msgs)
    print(total_records)

    ble_msgs.to_csv(outfile, header=True, columns = fields, index=False)



if __name__=="__main__":
    main()