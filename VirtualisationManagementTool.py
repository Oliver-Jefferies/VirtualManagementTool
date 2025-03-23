import threading

from flask import Flask, request, jsonify, render_template
import libvirt
import os
import sys
import time
from threading import Thread
from xml.etree.ElementTree import fromstring
import xml

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


def generate_mac_address():
    """Generate a random MAC address for the VM."""
    return "52:54:00:{:02x}:{:02x}:{:02x}".format(
        os.urandom(1)[0], os.urandom(1)[0], os.urandom(1)[0]
    )

def create_vm(vm_data):
    """Create a single VM using the provided data."""
    vm_name = vm_data.get('vm_name')
    base_disk = vm_data.get('base_disk')
    iso_image = vm_data.get('iso_image')
    memory_mb = vm_data.get('memory', 1024)  # Default 1GB
    cpus = vm_data.get('cpus', 1)  # Default 1 CPU
    mac_address = vm_data.get('mac_address', generate_mac_address())

    if not vm_name or not base_disk or not iso_image:
        return {"vm_name": vm_name, "status": "error", "message": "Missing required parameters"}

    base_disk = os.path.abspath(base_disk)
    vm_disk = os.path.join("/home/oliver/VMs", f"{vm_name}.qcow2")

    if not os.path.exists(base_disk):
        return {"vm_name": vm_name, "status": "error", "message": f"Base disk {base_disk} not found"}

    # Create a new VM disk
    os.system(f"qemu-img create -f qcow2 {vm_disk} 10G")

    # Convert memory to KiB
    memory_kib = memory_mb * 1024

    # Define the VM XML dynamically
    xml_config = f"""
    <domain type='kvm'>
      <name>{vm_name}</name>
      <memory unit='KiB'>{memory_kib}</memory>
      <vcpu placement='static'>{cpus}</vcpu>
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
        </disk>
        <interface type='network'>
          <mac address='{mac_address}'/>
          <source network='default'/>
          <model type='virtio'/>
        </interface>
      </devices>
    </domain>
    """

    try:
        domain = conn.lookupByName(vm_name)
        return {"vm_name": vm_name, "status": "error", "message": "VM already exists"}
    except libvirt.libvirtError:
        domain = conn.defineXML(xml_config)
        if domain is None:
            return {"vm_name": vm_name, "status": "error", "message": "Failed to create VM"}

        # **Start the VM immediately after creation**
    try:
        domain.create()
        return {"vm_name": vm_name, "status": "success", "message": "VM created and started successfully"}
    except libvirt.libvirtError as e:
        return {"vm_name": vm_name, "status": "error", "message": f"VM created but failed to start: {str(e)}"}


@app.route('/create_vm', methods=['POST'])
def create_vm_route():
    """
    API Route to create one or multiple VMs.
    Accepts either a single VM dictionary or a list of VM dictionaries.
    """
    data = request.json

    if isinstance(data, list):  # If multiple VMs
        results = []
        threads = []

        for vm_data in data:
            thread = threading.Thread(target=lambda d=vm_data: results.append(create_vm(d)))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        return jsonify({"status": "success", "results": results})

    elif isinstance(data, dict):  # If single VM
        result = create_vm(data)
        return jsonify(result)

    else:
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400


#Start VM Route
@app.route('/start_vm', methods=['POST'])
def start_vm():
    """
    Start a single VM or multiple VMs based on a base name.
    """
    data = request.json
    base_name = data.get('base_name')
    single_vm_name = data.get('vm_name')
    is_bulk = data.get('bulk', False)  # Determines if bulk mode is enabled

    try:
        started_vms = []
        failed_vms = []

        if is_bulk and base_name:  # Bulk start
            all_vms = [domain.name() for domain in conn.listAllDomains()]
            matching_vms = [vm for vm in all_vms if vm.startswith(base_name)]

            if not matching_vms:
                return jsonify({"status": "error", "message": f"No VMs found with base name {base_name}"}), 404

            for vm_name in matching_vms:
                try:
                    domain = conn.lookupByName(vm_name)
                    if not domain.isActive():
                        domain.create()
                        started_vms.append(vm_name)
                    else:
                        failed_vms.append({"vm_name": vm_name, "message": "Already running"})
                except libvirt.libvirtError as e:
                    failed_vms.append({"vm_name": vm_name, "message": str(e)})

            return jsonify({"status": "success", "started_vms": started_vms, "failed_vms": failed_vms})

        elif single_vm_name:  # Single start
            domain = conn.lookupByName(single_vm_name)
            if domain.isActive():
                return jsonify({"status": "error", "message": f"VM {single_vm_name} is already running"}), 400

            domain.create()
            return jsonify({"status": "success", "message": f"VM {single_vm_name} started successfully"})

        else:
            return jsonify({"status": "error", "message": "Invalid request"}), 400

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": f"Failed to start VM(s): {str(e)}"}), 500

@app.route('/delete_vm', methods=['POST'])
def delete_vm():
    """
    Delete a single VM or multiple VMs based on a base name.
    This will also delete the VM disk file.
    """
    data = request.json
    base_name = data.get('base_name')
    single_vm_name = data.get('vm_name')
    is_bulk = data.get('bulk', False)  # Determines if bulk mode is enabled

    try:
        deleted_vms = []
        failed_vms = []

        if is_bulk and base_name:  # Bulk delete
            all_vms = [domain.name() for domain in conn.listAllDomains()]
            matching_vms = [vm for vm in all_vms if vm.startswith(base_name)]

            if not matching_vms:
                return jsonify({"status": "error", "message": f"No VMs found with base name {base_name}"}), 404

            for vm_name in matching_vms:
                try:
                    domain = conn.lookupByName(vm_name)
                    if domain.isActive():
                        domain.destroy()  # Ensure VM is stopped before deletion
                    domain.undefine()  # Remove from libvirt
                    vm_disk = os.path.join("/home/oliver/VMs", f"{vm_name}.qcow2")

                    if os.path.exists(vm_disk):  # Delete VM disk
                        os.remove(vm_disk)

                    deleted_vms.append(vm_name)
                except libvirt.libvirtError as e:
                    failed_vms.append({"vm_name": vm_name, "message": str(e)})

            return jsonify({"status": "success", "deleted_vms": deleted_vms, "failed_vms": failed_vms})

        elif single_vm_name:  # Single delete
            try:
                domain = conn.lookupByName(single_vm_name)
                if domain.isActive():
                    domain.destroy()  # Stop VM before deletion
                domain.undefine()  # Remove from libvirt
                vm_disk = os.path.join("/home/oliver/VMs", f"{single_vm_name}.qcow2")

                if os.path.exists(vm_disk):  # Delete VM disk
                    os.remove(vm_disk)

                return jsonify({"status": "success", "message": f"VM {single_vm_name} deleted successfully"})
            except libvirt.libvirtError as e:
                return jsonify({"status": "error", "message": f"Failed to delete VM {single_vm_name}: {str(e)}"}), 500

        else:
            return jsonify({"status": "error", "message": "Invalid request"}), 400

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": f"Failed to delete VM(s): {str(e)}"}), 500


# Route to stop a VM
@app.route('/stop_vm', methods=['POST'])
def stop_vm():
    """
    Stop a single VM or multiple VMs based on a base name.
    """
    data = request.json
    base_name = data.get('base_name')
    single_vm_name = data.get('vm_name')
    is_bulk = data.get('bulk', False)  # Determines if bulk mode is enabled

    try:
        stopped_vms = []
        failed_vms = []

        if is_bulk and base_name:  # Bulk stop
            all_vms = [domain.name() for domain in conn.listAllDomains()]
            matching_vms = [vm for vm in all_vms if vm.startswith(base_name)]

            if not matching_vms:
                return jsonify({"status": "error", "message": f"No VMs found with base name {base_name}"}), 404

            for vm_name in matching_vms:
                try:
                    domain = conn.lookupByName(vm_name)
                    if domain.isActive():
                        domain.destroy()
                        stopped_vms.append(vm_name)
                    else:
                        failed_vms.append({"vm_name": vm_name, "message": "Already stopped"})
                except libvirt.libvirtError as e:
                    failed_vms.append({"vm_name": vm_name, "message": str(e)})

            return jsonify({"status": "success", "stopped_vms": stopped_vms, "failed_vms": failed_vms})

        elif single_vm_name:  # Single stop
            domain = conn.lookupByName(single_vm_name)
            if not domain.isActive():
                return jsonify({"status": "error", "message": f"VM {single_vm_name} is already stopped"}), 400

            domain.destroy()
            return jsonify({"status": "success", "message": f"VM {single_vm_name} stopped successfully"})

        else:
            return jsonify({"status": "error", "message": "Invalid request"}), 400

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": f"Failed to stop VM(s): {str(e)}"}), 500





@app.route('/vm_stats/<string:vm_name>', methods=['GET'])
def get_vm_stats(vm_name):
    try:
        conn = connect_to_hypervisor()
        domain = conn.lookupByName(vm_name)

        if not domain.isActive():
            return jsonify({"status": "error", "message": f"VM {vm_name} is not running"}), 400

        #Fetch Interface
        iface = "vnet0"

        # Interface stats
        net_stats = domain.interfaceStats(iface)
        print(net_stats)
        print(net_stats[0], net_stats[4])

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
        memory_max_stats = domain.maxMemory()
        memory_max = memory_max_stats / 1024

        return jsonify({
            "status": "success",
            "stats": {
                "vm_name": vm_name,
                "cpu_load": round(cpu_load, 2),
                "memory_used": round(memory_used, 2),
                "memory_max": memory_max,
                "net_stats_in": net_stats[0] * 0.000001 / interval,
                "net_stats_out": net_stats[4] * 0.000001 / interval,
            }
        })

    except libvirt.libvirtError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":

    # Run the Flask app
    app.run(debug=True, port=5000)
