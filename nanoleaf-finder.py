from multiprocessing.dummy import Process, Queue, Pipe
import ipaddress
import sys
import requests
import logging
import socket
import sys

# setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

found = False

def worker(queue, conn):
    ip = queue.get()
    api_endppoint = f'http://{ip}:16021/api/v1/new'
    try:
        r = requests.get(api_endppoint,timeout=1)
        if r.status_code == 200:
            conn.send(ip)
            conn.close()
    except requests.exceptions.ConnectionError:
        logger.info(f'Connection error: {ip}')

def getnet(q):
    local_ip = socket.gethostbyname(socket.gethostname())
    logger.info('Local IP: %s', local_ip)

    # create network address from local IP
    # assuming /24
    splits = local_ip.split('.')
    splits[-1] = '0'
    network_addr = '.'.join(splits)
    logger.info('Network address: %s', network_addr)
    
    network = ipaddress.IPv4Network(network_addr + '/24')

    for net in network:
        q.put(net)
    
    return network

def readerd(conn):
    global found
    while True:
        data = conn.recv()
        if not data:
            break
        logger.info(f'Found: {data}')
        found = True
        sys.exit(0)

if __name__ == '__main__':
    q = Queue()

    network = getnet(q)
    logger.info('Network: %s', network)
    parent_conn, child_conn = Pipe()

    procs = [Process(target=readerd, args=(parent_conn,))]
    for ip in network:
        procs.append(Process(target=worker, args=(q, child_conn)))

    for proc in procs:
        proc.start()

    for proc in procs:
        proc.join()

    if q.qsize() == 0 and not found:
        logger.error('No nanoleaf found')
        sys.exit(1)

    # create a queue to share data between processes
    
   