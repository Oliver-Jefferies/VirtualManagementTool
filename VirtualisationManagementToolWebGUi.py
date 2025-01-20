from flask import Flask, request, jsonify, render_template
import libvirt
import os
import sys
import time
from threading import Thread

app = Flask(__name__)

@app.route("/")
def index():
        return render_template("index.html")
# Connect to the system's hypervisor
def connect_to_hypervisor():
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)
    return conn

conn = connect_to_hypervisor()  # Establish connection globally


# Route to create a VM
@app.route('/create_vm', methods=['POST'])
def create_vm_route():
    data = request.json
    vm_name = data['vm_name']
    base_disk = data['base_disk']
    iso_image = data['iso_image']

    vm_disk = f"/home/oliver/VMs/{vm_name}.qcow2"
    os.system(f"qemu-img convert -f qcow2 -O qcow2 {base_disk} {vm_disk}")

    # Define the VM XML dynamically
    xml_config = f"""
    <domain type='kvm'>
      <name>{vm_name}</name>
      <memory unit='KiB'>1048576</memory>
      <vcpu placement='static'>1</vcpu>
      <os>
        <type arch='x86_64' machine='pc'>hvm</type>
        <boot dev='hd'/>
        <boot dev='cdrom'/>
        <cdrom>
          <source file='{iso_image}'/>
          <target dev='hdc' bus='ide'/>
          <readonly/>
        </cdrom>
      </os>
      <devices>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='{vm_disk}'/>
          <target dev='vda' bus='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
        </disk>
        <interface type='network'>
          <mac address='52:54:00:6b:29:55'/>
          <source network='default'/>
          <model type='virtio'/>
        </interface>
      </devices>
    </domain>
    """

    try:
        domain = conn.lookupByName(vm_name)
        return jsonify({"status": "error", "message": f"VM {vm_name} already exists."}), 400
    except libvirt.libvirtError:
        domain = conn.defineXML(xml_config)
        if domain is None:
            return jsonify({"status": "error", "message": f"Failed to create VM {vm_name}."}), 500
        return jsonify({"status": "success", "message": f"VM {vm_name} created successfully."})


# Route to start a VM
@app.route('/start_vm', methods=['POST'])
def start_vm_route():
    data = request.json
    vm_name = data['vm_name']

    try:
        domain = conn.lookupByName(vm_name)
        if domain.isActive():
            return jsonify({"status": "info", "message": f"VM {vm_name} is already running."})
        domain.create()
        return jsonify({"status": "success", "message": f"VM {vm_name} started successfully."})
    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to stop a VM
@app.route('/stop_vm', methods=['POST'])
def stop_vm_route():
    data = request.json
    vm_name = data['vm_name']

    try:
        domain = conn.lookupByName(vm_name)
        if domain.isActive():
            domain.destroy()
            return jsonify({"status": "success", "message": f"VM {vm_name} stopped successfully."})
        return jsonify({"status": "info", "message": f"VM {vm_name} is already stopped."})
    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get VM stats
@app.route('/vm_stats/<vm_name>', methods=['GET'])
def get_vm_stats_route(vm_name):
    try:
        domain = conn.lookupByName(vm_name)
        if not domain.isActive():
            return jsonify({"status": "info", "message": f"VM {vm_name} is not running."})

        # CPU stats
        cpu_stats = domain.getCPUStats(True)
        cpu_time = cpu_stats[0]['cpu_time'] / 1e9  # Convert to seconds

        # Memory stats
        mem_stats = domain.memoryStats()
        memory_used = mem_stats.get('rss', 0) / 1024  # Convert to MB

        stats = {
            "vm_name": vm_name,
            "cpu_time": f"{cpu_time:.2f} seconds",
            "memory_used": f"{memory_used:.2f} MB"
        }

        return jsonify({"status": "success", "stats": stats})

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Performance monitoring thread
def monitor_vms():
    while True:
        # Example VMs to monitor
        vm_names = ["UbuntuBaseVM"]
        for vm_name in vm_names:
            try:
                domain = conn.lookupByName(vm_name)
                if domain.isActive():
                    print(f"VM {vm_name} is running.")
                else:
                    print(f"VM {vm_name} is not running.")
            except libvirt.libvirtError:
                print(f"VM {vm_name} not found.")
        time.sleep(10)  # Monitor every 10 seconds


if __name__ == "__main__":
    # Start the monitoring thread
    monitor_thread = Thread(target=monitor_vms, daemon=True)
    monitor_thread.start()

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
