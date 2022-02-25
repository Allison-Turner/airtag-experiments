#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mpc
import re

raw_sdr_output_file="airtag_out.txt"
csv_outfile = "airtag_long_scan.csv"
png_outfile = "intervals.png"

#                    0                        1             2              3              4                    5     6     7                 8                   9                         10
fields           = ['us_since_last_capture', 'packet_num', 'channel_num', 'access_addr', 'pdu',               'tx', 'rx', 'payload_length', 'advertising_addr', 'data',                   'crc']
field_junk_regex = ["us",                    "Pkt",        "Ch",          "AA:",         "ADV_PDU_t((\d)+):", "T",  "R",  "PloadL",         "AdvA:|A((\d)+):",  "Data:|A((\d)+):|Byte:",  "CRC"]
num_fields = len(fields)



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

    ble_msgs.to_csv(csv_outfile, header=True, columns = fields, index=False)



def read_ble_msgs_from_csv():
    ble_msgs = pd.read_csv(csv_outfile, header=0, names=fields, delimiter=',')
    for col in fields:
        if (col != 'access_addr') and (col != 'pdu') and (col != 'advertising_addr') and (col != 'data'):
            ble_msgs[col] = pd.to_numeric(ble_msgs[col], errors='coerce')
    
    ble_msgs = ble_msgs.sort_values(by=fields[1])

    return ble_msgs

def generate_time_from_start_vals(ble_msgs):
    ble_msgs = ble_msgs.sort_values(by=fields[1])
    ts = 0
    ts_arr = []

    for i in range(len(ble_msgs)):
        ts = ts + ble_msgs.at[i, fields[0]]
        ts_arr.append(ts)

    dur_secs = ts / 1000000.0
    dur_mins = dur_secs / 60.0
    dur_hrs = dur_mins / 60.0

    print("Total scan duration: " + str(dur_hrs) + " hours")

    return pd.Series(ts_arr)

def graph_packet_capture_intervals(ble_msgs):
    
    adv_ind_msgs = ble_msgs.loc[ble_msgs[fields[4]] == 'ADV_IND']
    other_msgs = ble_msgs.loc[ble_msgs[fields[4]] != 'ADV_IND']


    xmin = ble_msgs[fields[1]].min()
    xmax = ble_msgs[fields[1]].max()
    xrange = xmax - xmin

    ymin = ble_msgs[fields[0]].min()
    ymax = ble_msgs[fields[0]].max()
    yrange = ymax - ymin

    fig, ax = plt.subplots()
    fig.set_size_inches(20, 20)
    plt.title('Apple Airtag BLE Advertisement Frequency Over 2+ Days of Faraday Cage Isolation')
    plt.xlabel('Packet Number')
    plt.ylabel('Microseconds Since Last Packet')
    ax.axis([(xmin - (xrange * 0.05)), (xmax + (xrange * 0.05)), (ymin - (yrange * 0.05)), (ymax + (yrange * 0.05))])


    unique_adv_addrs_adv_ind = adv_ind_msgs[fields[8]].unique()
    unique_adv_addrs_other_pdu = other_msgs[fields[8]].unique()

    pnum_of_first_adv_addr_occurence = []

    steps = np.linspace(start=0.0, stop=1.0, num=(len(unique_adv_addrs_adv_ind) + len(unique_adv_addrs_other_pdu)))
    color_map = plt.cm.get_cmap('Spectral')
    addr_colors = list(map((lambda x : mpc.rgb2hex(color_map(x))), steps))
    c_i = 0

    for adv_addr in unique_adv_addrs_adv_ind:
        ix = adv_ind_msgs.index[adv_ind_msgs[fields[8]] == adv_addr].tolist()
        
        if len(ix) > 0:
            fst = min(ix)
            pnum_of_first_adv_addr_occurence.append(adv_ind_msgs.at[fst, fields[1]])
            rows = adv_ind_msgs.loc[adv_ind_msgs[fields[8]] == adv_addr]

            ax.scatter(rows[fields[1]], rows[fields[0]], c=addr_colors[c_i], alpha=0.5)
            c_i += 1

        #Strip null value
        else:
            np.delete(unique_adv_addrs_adv_ind, np.where(unique_adv_addrs_adv_ind==adv_addr))


    for adv_addr in unique_adv_addrs_other_pdu:
        ix = other_msgs.index[other_msgs[fields[8]] == adv_addr].tolist()
        
        if len(ix) > 0:
            fst = min(ix)
            pnum_of_first_adv_addr_occurence.append(other_msgs.at[fst, fields[1]])
            rows = other_msgs.loc[other_msgs[fields[8]] == adv_addr]

            ax.scatter(rows[fields[1]], rows[fields[0]], c=addr_colors[c_i])
            c_i += 1

        #Strip null value
        else:
            np.delete(unique_adv_addrs_other_pdu, np.where(unique_adv_addrs_other_pdu==adv_addr))



    firsts = pd.DataFrame(columns=fields)

    for pnum in pnum_of_first_adv_addr_occurence:
        row = ble_msgs.loc[ble_msgs[fields[1]] == pnum]
        firsts = pd.concat([ firsts, row ])

    firsts.to_csv('first_appearance_of_adv_addr.csv', index=False)

    plt.grid()
    plt.savefig(png_outfile, dpi=200)

    plt.cla()
    plt.clf()



def main():
    #convert_btle_rx_logs_to_csv()

    ble_msgs = read_ble_msgs_from_csv()

    graph_packet_capture_intervals(ble_msgs)

    #generate_time_from_start_vals(ble_msgs)


if __name__=="__main__":
    main()