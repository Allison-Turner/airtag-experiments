#!/usr/bin/env python3
import pandas as pd
import re
import matplotlib.pyplot as plt
import numpy as np

raw_sdr_output_file="airtag_out.txt"
csv_outfile = "airtag_long_scan.csv"
png_outfile = "intervals.png"

#                0            1             2              3              4      5         6         7                 8                   9       10
fields       = ['timestamp', 'packet_num', 'channel_num', 'access_addr', 'pdu', 'tx',     'rx',     'payload_length', 'advertising_addr', 'data', 'crc']
field_dtypes = [np.int64,     np.int64,     np.int64,      str,           str,       np.int64, np.int64, np.int64,         str,                str,    np.int64]
field_dtype_dict = dict(zip(fields, field_dtypes))

num_fields = len(fields)

field_junk_regex = ["us", "Pkt", "Ch", "AA:", "ADV_PDU_t((\d)+):", "T", "R", "PloadL", "AdvA:|A((\d)+):", "Data:|A((\d)+):", "CRC"]



def remove_data_labels(raw):
    clean = raw

    for i, row in raw.iterrows():
        field_shift = 0

        for j in range(num_fields):
            
            raw_str = str(raw.at[i, fields[j]])
            pattern = field_junk_regex[j]

            clean_str = re.sub(pattern, '', raw_str)

            if j==4:
                if 'RESERVED' in clean_str:
                    field_shift = 1

                clean.at[i, fields[j]] = clean_str

            elif j==8 and field_shift==1:
                clean.at[i, fields[j]] = None
                j = j + 1
                raw_str = str(raw.at[i, fields[j]])
                clean.at[i, fields[j]] = clean_str
                clean.at[i, fields[j+1]] = raw_str

            else:
                clean.at[i, fields[j]] = clean_str
    
    return clean



def convert_btle_rx_logs_to_csv():
    dataLog = []
    with open(raw_sdr_output_file, 'rt') as f:
        data = f.readlines()
    for line in data:
        if 'Error' in line:
            dataLog.append(line)

    error_entries = pd.DataFrame(columns=fields)

    for entry in dataLog:
        halves = entry.split('Error')
        tokens = halves[0].split(' ')[:8] + [None, None, None]
        data_line = pd.DataFrame([tokens], columns=fields)

        for i in range(8):
            raw_str = str(data_line.at[0, fields[i]])
            pattern = field_junk_regex[i]
            clean_str = re.sub(pattern, '', raw_str)
            data_line.at[0, fields[i]] = clean_str

        error_entries = pd.concat([error_entries, data_line])


    ble_msgs_raw = pd.read_csv(raw_sdr_output_file, names=fields, delimiter=' ', skiprows=6, on_bad_lines='skip')

    total_raw_records  = len(ble_msgs_raw)
    ble_msgs_raw = ble_msgs_raw.drop(range((total_raw_records - 3), total_raw_records))
    ble_msgs = remove_data_labels(ble_msgs_raw)
    ble_msgs = pd.concat([ble_msgs, error_entries])

    total_records = len(ble_msgs)
    print(total_records)

    print(ble_msgs[fields[4]].unique())

    ble_msgs.to_csv(csv_outfile, header=True, columns = fields, index=False)



def graph_packet_capture_intervals(ble_msgs):
    adv_ind_msgs = ble_msgs
    other_msgs = pd.DataFrame(columns=fields)

    for i, row in ble_msgs.iterrows():
        if (row[fields[4]] != 'ADV_IND'):
            adv_ind_msgs = adv_ind_msgs.drop(i)
            other_msgs = other_msgs.append(ble_msgs.iloc[i])

    print(len(adv_ind_msgs))
    print(len(other_msgs))

    xmin = ble_msgs[fields[1]].min()
    xmax = ble_msgs[fields[1]].max()
    xrange = xmax - xmin

    ymin = ble_msgs[fields[0]].min()
    ymax = ble_msgs[fields[0]].max()
    yrange = ymax - ymin

    fig, ax = plt.subplots()
    fig.set_size_inches(10, 14)
    plt.title('Apple Airtag BLE Advertisement Frequency Over 2+ Days of Faraday Cage Isolation')
    plt.xlabel('Packet Number')
    plt.ylabel('Microseconds Since Last Packet')
    ax.axis([(xmin - (xrange * 0.1)), (xmax + (xrange * 0.1)), (ymin - (yrange * 0.1)), (ymax + (yrange * 0.1))])

    adv_ind_scatter = ax.scatter(adv_ind_msgs[fields[1]], adv_ind_msgs[fields[0]], c='#00cecb', alpha=0.5)
    other_pdu_scatter = ax.scatter(other_msgs[fields[1]], other_msgs[fields[0]], c='#ff5b5e', alpha=0.7)
    plt.grid()

    plt.savefig(png_outfile, dpi=200)

    plt.cla()
    plt.clf()



def main():
    convert_btle_rx_logs_to_csv()

    ble_msgs = pd.read_csv(csv_outfile, header=0, names=fields, delimiter=',')#, dtype=field_dtype_dict
    for col in fields:
        if (col != 'access_addr') and (col != 'pdu') and (col != 'advertising_addr') and (col != 'data'):
            ble_msgs[col] = pd.to_numeric(ble_msgs[col], errors='coerce')

    graph_packet_capture_intervals(ble_msgs)

    print(ble_msgs[fields[8]].unique())

if __name__=="__main__":
    main()