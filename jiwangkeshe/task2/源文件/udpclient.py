import socket
import time
import sys
import struct
import statistics

# 配置
TIMEOUT = 0.1  # 100ms则超时
VERSION = 2  # 版本号
HEADER_SIZE = 203  # 头部大小
DATA_SIZE = 0  # 数据部分大小，因为187字节是填充，不包含实际数据
RETRIES = 2  # 重传次数
REQUESTS_SENT = 12  # 要发送的请求数

# 创建数据包
def packet_creat(seq_no, id_of_client, req_type):
    data_len = (HEADER_SIZE - 187).to_bytes(2, 'big')  # 实际数据长度
    timestamp = int(time.time()).to_bytes(4, 'big')    # 时间戳
    client_status = b'\x00\x01'  # 客户端状态
    filling = b'a' * 187  # 数据部分填充'a'
    packet = (
            struct.pack('!H', seq_no) +
            struct.pack('B', VERSION) +
            data_len +
            struct.pack('B', req_type) +
            id_of_client +
            timestamp +
            client_status +
            filling
    )
    return packet

# 解析响应数据包
def resppacket_parse(packet):
    seq_no = struct.unpack('!H', packet[:2])[0]  # 序列号
    version = packet[2]  # 版本号
    system_time = int.from_bytes(packet[3:11], 'big')  # 系统时间
    data_len = struct.unpack('!H', packet[11:13])[0]  # 数据长度
    resp_type = packet[13]  # 响应状态/类型
    server_status_code = struct.unpack('!H', packet[14:16])[0]  # 服务器状态码
    return seq_no, version, system_time, data_len, resp_type, server_status_code

def main(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建UDP套接字
    client_socket.settimeout(TIMEOUT)  # 设置超时时间

    rtt_sets = []  # 储存RTT数值
    packets_received = 0  # 接收的数据包计数
    packets_sent = 0
    first_resp_time = None  # 第一个响应时间
    last_resp_time = None  # 最后一个响应时间

    id_of_client = b'clnt'  # 客户端ID

    # 发送SYN包进行连接建立
    seq_no = 0  # 将三次握手发送的数据包序列号都设置为0
    syn_packet = packet_creat(seq_no, id_of_client, 1)  # 请求类型1表示SYN
    client_socket.sendto(syn_packet, (server_ip, server_port))

    # 接收server端的SYN-ACK响应数据包
    try:
        syn_ack_resp_packet, _ = client_socket.recvfrom(HEADER_SIZE + DATA_SIZE)
        seq_no_resp, version_resp, timestamp, data_len, resp_type, server_status_code = resppacket_parse(syn_ack_resp_packet)

        if resp_type == 2:  # 接收到server端的SYN-ACK
            # 发送ACK确认包
            ack_packet = packet_creat(seq_no, id_of_client, 3)  # 请求类型3表示ACK
            client_socket.sendto(ack_packet, (server_ip, server_port))
    except socket.timeout:
        print("Sorry, connection attempt failed.")
        return

    # 发送12个数据包
    for seq_no in range(1, REQUESTS_SENT + 1):
        packet = packet_creat(seq_no, id_of_client, 4)  # 请求类型4表示数据传输
        have_tried = 0
        while have_tried <= RETRIES:
            try:
                time_start = time.time()  # 记录开始时间
                client_socket.sendto(packet, (server_ip, server_port))  # 发送数据包
                packets_sent += 1
                response_packet, _ = client_socket.recvfrom(HEADER_SIZE + DATA_SIZE)  # 接收响应数据包
                time_end = time.time()  # 记录结束时间

                calRtt = (time_end - time_start) * 1000  # 计算RTT（单位：毫秒）
                seq_no_resp, version_resp, timestamp, data_len, resp_type, server_status_code = resppacket_parse(response_packet)  # 解析响应数据包

                if seq_no_resp == seq_no and version_resp == VERSION:  # 验证序列号和版本号
                    packets_received += 1
                    rtt_sets.append(calRtt)

                    if first_resp_time is None:
                        first_resp_time = time.time()    # 记录第一次响应的系统时间
                    last_resp_time = time.time()     # 记录最后一次响应的系统时间

                    print(
                        f"Seq no: {seq_no}, {server_ip}:{server_port}, RTT: {calRtt:.2f} ms")
                    break
            except socket.timeout:
                have_tried += 1
                if have_tried > RETRIES:
                    print(f"Seq no: {seq_no}, request time out")
                else:
                    print(f"Seq no: {seq_no}, retrying... ({have_tried}/{RETRIES})")

    # 发送FIN包进行连接释放
    seq_no = 0  # 将四次挥手发送的数据包序列号都设置为0
    fin_packet = packet_creat(seq_no, id_of_client, 5)  # 请求类型5表示FIN
    client_socket.sendto(fin_packet, (server_ip, server_port))

    # 接收server端的FIN-ACK响应数据包
    try:
        response1_packet, _ = client_socket.recvfrom(HEADER_SIZE + DATA_SIZE)
        seq_no_resp1, ver_resp1, timestamp1, data_len1, resp_type1, server_status_code1 = resppacket_parse(response1_packet)

        response2_packet, _ = client_socket.recvfrom(HEADER_SIZE + DATA_SIZE)
        seq_no_resp2, ver_resp2, timestamp2, data_len2, resp_type2, server_status_code2 = resppacket_parse(response2_packet)

        if resp_type1 == 6 and resp_type2 == 7:  # 接收server端的FIN-ACK和server端的FIN
            # 发送LAST_ACK确认包
            last_ack_packet = packet_creat(seq_no, id_of_client, 8)  # 请求类型8表示client端的ACK
            client_socket.sendto(last_ack_packet, (server_ip, server_port))
    except socket.timeout:
        print("Sorry, connection release attempt failed.")

    if rtt_sets:
        max_rtt = max(rtt_sets)
        min_rtt = min(rtt_sets)
        avg_rtt = sum(rtt_sets) / len(rtt_sets)
        stddev_rtt = statistics.stdev(rtt_sets)
    else:
        max_rtt = min_rtt = avg_rtt = stddev_rtt = 0.0

    loss_rate = ((packets_sent - packets_received) / packets_sent) * 100
    # 计算服务器整体响应时间
    server_response_time = (last_resp_time - first_resp_time) * 1000 if first_resp_time and last_resp_time else 0

    print("\nSummary Information:")
    print(f"Received UDP packets: {packets_received}")
    print(f"Packet loss rate: {loss_rate:.2f}%")
    print(f"Max RTT: {max_rtt:.2f} ms")
    print(f"Min RTT: {min_rtt:.2f} ms")
    print(f"Avg RTT: {avg_rtt:.2f} ms")
    print(f"RTT Stddev: {stddev_rtt:.2f}")
    print(f"Server response time difference: {server_response_time:.2f} ms")

    client_socket.close()  # 关闭套接字

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)
        
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    main(server_ip, server_port)
