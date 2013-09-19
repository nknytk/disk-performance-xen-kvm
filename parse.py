# coding: utf-8

import os
import sys
import re

#    rw = 'read' if iodirection == 'r' else 'write'
#    condition = '%s_%s_%s' % (iosize, rw, iodepth)
#    with open(dirname + '/' + condition + '.txt') as f:

def main(dirs):
    testsizes = ['11', '512', '4k', '32k', '512k', '1m']
    for size in testsizes:
        for rw in ('read', 'write'):
            condition = size + '_' + rw + '_1'
            results = []
            for name in dirs:
                result = parse_fio_result(name, condition)
                result['name'] = name
                result['host_io_util'] = host_io_util(name + '/iostat_host.txt', result['start'], result['end'])
                if os.path.exists(name + '/xentop.txt'):
                    cpuinfo = host_xentop(name + '/xentop.txt',  result['start'], result['end'])
                    result['host_cpu'] = cpuinfo[0]
                    result['vm_cpu'] = cpuinfo[1]
                elif os.path.exists(name + '/top_host.txt'):
                    cpuinfo = host_top(name + '/top_host.txt',  result['start'], result['end'])
                    result['host_cpu'] = cpuinfo[0]
                    result['vm_cpu'] = cpuinfo[1]
                results.append(result)
            print condition
            merge_print(results)

def listup_dirs():
    pass

def parse_fio_result(dirname, condition):
    filename = dirname + '/fio_' + condition + '.txt'
    with open(filename) as f:
        rawdata = f.readlines()

    stage = 0
    for line in rawdata:
        # テスト結果の中身が現れるまでは飛ばす
        if stage == 0:
            if line.startswith(condition + ': (groupid='):
                stage = 1

        # 帯域、IOPS、テスト実行時間を取得
        elif stage == 1:
            result = dict([kv.strip().split('=') for kv in line.split(':')[1].split(',')])
            result['iops'] = int(result['iops'])
            result['runt'] = int(result['runt'][:-7])
            if result['bw'].endswith('KB/s'):
                result['bw'] = float(result['bw'].replace('KB/s', ''))
            elif result['bw'].endswith('MB/s'):
                result['bw'] = float(result['bw'].replace('MB/s', '')) * 1000
            elif result['bw'].endswith(' B/s'):
                result['bw'] = float(result['bw'].replace(' B/s', '')) / 1000

            stage = 2

        # latency分布が現れるまで飛ばす。bw (KB/s) で始まる行の次の行からlatency分布
        elif stage == 2:
            if line.strip().startswith('bw '):
                stage = 3
                lat_distribution = {}

        # latency分布の取得　直後にCPU使用量もあるのでそれも取得
        elif stage == 3:
            line = line.strip().replace('%', '')
            if line.startswith('cpu'):
		cpu = dict([kv.strip().split('=') for kv in line.split(':')[1].split(',')])
                result['guest_cpu'] = float(cpu['usr']) + float(cpu['sys'])
                result['latency'] = lat_distribution
                stage = 4
                continue

            if line.startswith('lat (usec)'):
                unitfactor = 0.001
            elif line.startswith('lat (msec)'):
                unitfactor = 1
            elif line.startswith('lat (sec)'):
                unitfactor = 1000

            data = line.split(':')[1]
            for datum in data.split(','):
                k, v = datum.strip().strip('>=').split('=')
                lat_distribution[float(k) * unitfactor] = float(v)

        # ゲストのディスクIO使用量を取得
        elif stage == 4:
            line = line.strip()
            header = line.split(':')[0]
            if header in ('sda', 'vda', 'xvda'):
                result ['guest_io_util'] = float(line.split('util=')[1].replace('%', ''))
                stage = 5

        # 準備期間を除いたテストの開始・終了時間を取得
        elif stage == 5:
            if line.startswith(condition):
                hms = line.split(' ')[-2] if line.endswith('JST\n') else line.split(' ')[-3]
                result['end'] = int(hms[:2]) * 3600 + int(hms[3:5]) * 60 + int(hms[6:])
                result['start'] = result['end'] - result['runt']
                return result

def host_io_util(filename, start, end):
    if not os.path.exists(filename):
        return 0
    with open(filename) as f:
        data = f.readlines()

    cnt, util_sum = 0, 0
    for line in data:
        if line.find(' sda ') == -1:
            continue
        rtime = int(line[:2]) * 3600 + int(line[3:5]) * 60 + int(line[6:8])
        if not start <= rtime <= end:
            continue
        util_sum += float(re.sub(' +', ' ', line).split(' ')[12].strip())
        cnt += 1

    if cnt == 0:
        return 0
    else:
        return util_sum/cnt

def host_top(filename, start, end):
    if not os.path.exists(filename):
        return (0, 0)

    cnt, hostcpu_sum, vmcpu_sum = 0, 0, 0
    with open(filename) as f:
        data = f.readlines()

    for line in data:
        if line.strip() == '':
            continue
        rtime = int(line[:2]) * 3600 + int(line[3:5]) * 60 + int(line[6:8])
        if not start <= rtime <= end:
            continue
        fields = re.sub(' +', ' ', line).strip().split(' ')
        if len(fields) < 12:
            continue
        if fields[1] == 'top':
            cnt += 1
            continue
        if not re.match('^[0-9]+$', fields[1]): 
            continue

        hostcpu_sum += float(fields[9])
        if line.find('qemu-kvm') != -1:
            vmcpu_sum += float(fields[9])

    hostcpu_avg = hostcpu_sum / cnt
    vmcpu_avg = vmcpu_sum / cnt
    return (hostcpu_avg, vmcpu_avg)

def host_xentop(filename, start, end):
    if not os.path.exists(filename):
        return (0, 0)

    cnt, hostcpu_sum, vmcpu_sum = 0, 0, 0
    with open(filename) as f:
        data = f.readlines()

    for line in data:
        if line.strip() == '':
            continue
        rtime = int(line[:2]) * 3600 + int(line[3:5]) * 60 + int(line[6:8])
        if not start <= rtime <= end:
            continue
        if line.find('Domain-0') != -1:
             hostcpu_sum += float(re.sub(' +', ' ', line).split(' ')[4].strip())
        elif line.find('NAME') != -1:
            cnt += 1
        else:
            vmcpu_sum += float(re.sub(' +', ' ', line).split(' ')[4].strip())

    hostcpu_avg = hostcpu_sum / cnt
    vmcpu_avg = vmcpu_sum / cnt
    return (hostcpu_avg, vmcpu_avg)

def merge_print(parsed_results):
    latency_keys = []
    for pv in parsed_results:
        latency_keys.extend(pv['latency'].keys())
    latency_keys = sorted(list(set(latency_keys)))

    header = ['name', 'bw', 'iops', 'guest_cpu', 'host_cpu', 'vm_cpu', 'guest_io_util', 'host_io_util']
    print '\t'.join(header + [str(k) for k in latency_keys])
    for pv in parsed_results:
        print '\t'.join([str(pv.get(k, 0)) for k in header] + [str(pv['latency'].get(k, 0)) for k in latency_keys])


if __name__ == '__main__':
    main(sys.argv[1:])
