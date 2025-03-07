from flask import Flask, request, jsonify, render_template
import libvirt
import os
import sys
import time
from threading import Thread

# Global dictionary to store previous CPU stats
previous_cpu_stats = {}

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

@app.route('/list_vms', methods=['GET'])
def list_vms():
    try:
        vms = []
        for domain_id in conn.listDomainsID():  # Get running VMs
            domain = conn.lookupByID(domain_id)
            vms.append({"name": domain.name(), "status": "on"})

        for name in conn.listDefinedDomains():  # Get stopped VMs
            vms.append({"name": name, "status": "off"})

        return jsonify({"status": "success", "vms": vms})
    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to create a VM
@app.route('/create_vm', methods=['POST'])
def create_vm_route():
    data = request.json
    vm_name = data['vm_name']
    base_disk = data['base_disk']
    iso_image = data['iso_image']
    memory_allocation = data.get('memory_allocation', 1024)  # Default to 1GB if not provided
    core_allocation = data.get('core_allocation', 2)


    vm_disk = f"/home/oliver/VMs/{vm_name}.qcow2"
    os.system(f"qemu-img convert -f qcow2 -O qcow2 {base_disk} {vm_disk}")

    memory_kib = memory_allocation * 1024  # Convert MB to KiB
    # Define the VM XML dynamically
    xml_config = f"""
    <domain type='kvm'>
      <name>{vm_name}</name>
      <memory unit='KiB'>{memory_kib}</memory>
      <vcpu placement='static'>{core_allocation}</vcpu>
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

#Start VM Route
@app.route('/start_vm', methods=['POST'])
def start_vm_route():
    data = request.json
    vm_name = data['vm_name']

    try:
        domain = conn.lookupByName(vm_name)

        if domain.isActive():
            return jsonify({"status": "info", "message": f"VM {vm_name} is already running."})

        # Start the VM
        domain.create()
        return jsonify({"status": "success", "message": f"VM {vm_name} started successfully."})

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": f"Failed to start VM: {str(e)}"}), 500


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





@app.route('/vm_stats/<string:vm_name>', methods=['GET'])
def get_vm_stats(vm_name):
    try:
        conn = connect_to_hypervisor()
        domain = conn.lookupByName(vm_name)

        if not domain.isActive():
            return jsonify({"status": "error", "message": f"VM {vm_name} is not running"}), 400

        # Fetch CPU stats
        cpu_stats = domain.getCPUStats(True)
        cpu_time = cpu_stats[0]['cpu_time'] / 1e9  # Convert nanoseconds to seconds

        # Calculate CPU load
        now = time.time()
        if vm_name in previous_cpu_stats:
            prev_time, prev_cpu_time = previous_cpu_stats[vm_name]
            interval = now - prev_time
            cpu_load = ((cpu_time - prev_cpu_time) / interval) * 100
        else:
            # First-time calculation
            cpu_load = 0.0

        # Update previous stats
        previous_cpu_stats[vm_name] = (now, cpu_time)

        # Fetch memory stats
        mem_stats = domain.memoryStats()
        memory_used = mem_stats.get('rss', 0) / 1024  # Convert to MB

        return jsonify({
            "status": "success",
            "stats": {
                "vm_name": vm_name,
                "cpu_load": round(cpu_load, 2),
                "memory_used": round(memory_used, 2),
            }
        })

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# Performance monitoring thread
#def monitor_vms():
#    while True:
#        # Example VMs to monitor
#        vm_names = ["UbuntuBaseVM"]
#        for vm_name in vm_names:
#            try:
#                domain = conn.lookupByName(vm_name)
#                if domain.isActive():
#                    print(f"VM {vm_name} is running.")
#                else:
#                    print(f"VM {vm_name} is not running.")
#            except libvirt.libvirtError:
#                print(f"VM {vm_name} not found.")
#        time.sleep(10)  # Monitor every 10 seconds


if __name__ == "__main__":

    # Run the Flask app
    app.run(debug=True, port=5000)
