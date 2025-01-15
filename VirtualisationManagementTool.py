import libvirt
import os
import sys
import time
import paramiko

# Connect to the system's hypervisor
def connect_to_hypervisor():
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)
    return conn


# Function to read the XML from an external file
def load_xml_from_file(xml_file_path):
    try:
        with open(xml_file_path, 'r') as xml_file:
            xml_config = xml_file.read()
        return xml_config
    except FileNotFoundError:
        print(f"Error: XML file {xml_file_path} not found.")
        return None


# Function to create the VM from the XML file
def create_vm(conn, vm_name, vm_disk, iso_image):
    # Dynamically generate the XML configuration for the VM
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
      <serial type='pty'>
  <target port='0'/>
</serial>
<console type='pty'>
  <target type='serial' port='0'/>
</console>
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
<channel type='unix'>
  <source mode='bind'/>
  <target type='virtio' name='org.qemu.guest_agent.0'/>
  <address type='virtio-serial' controller='0' bus='0' port='1'/>
</channel>
<graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
<graphics type='spice' autoport='yes'>
  <listen type='none'/>
</graphics>
      </devices>
    </domain>
    """

    try:
        # Check if the VM already exists
        domain = conn.lookupByName(vm_name)
        print(f"VM {vm_name} already exists.")
    except libvirt.libvirtError:
        # Define and create the VM from the XML configuration
        domain = conn.defineXML(xml_config)
        if domain is None:
            print(f'Error creating persistent VM {vm_name}.')
            exit(1)
        print(f'VM {vm_name} created successfully.')


# Create multiple VMs from the same ISO and disk base
def create_multiple_vms(conn, base_name, num_vms, base_disk, iso_image):
    """Create multiple VMs from the same ISO and disk base."""
    for i in range(1, num_vms + 1):
        vm_name = f"{base_name}_{i}"
        vm_disk = f"/home/oliver/VMs/{vm_name}.qcow2"

        # Create a full clone of the base disk for each VM
        os.system(f"qemu-img convert -f qcow2 -O qcow2 {base_disk} {vm_disk}")

        # Now create the VM using the full disk clone
        create_vm(conn, vm_name, vm_disk, iso_image)



# Function to start a VM by name
def start_vm(conn, vm_name):
    try:
        domain = conn.lookupByName(vm_name)
        if domain.isActive():
            print(f"VM {vm_name} is already running.")
        else:
            domain.create()  # Start the VM
            print(f"VM {vm_name} started.")
    except libvirt.libvirtError as e:
        print(f"Error starting VM {vm_name}: {str(e)}")


# Function to start all VMs
def start_all_vms(conn, base_name, num_vms):
    """Start all VMs that were created."""
    for i in range(1, num_vms + 1):
        vm_name = f"{base_name}_{i}"
        start_vm(conn, vm_name)


# Function to stop a VM by name
def stop_vm(conn, vm_name):
    try:
        domain = conn.lookupByName(vm_name)
        if domain.isActive():
            domain.destroy()  # Stop the VM
            print(f"VM {vm_name} stopped.")
        else:
            print(f"VM {vm_name} is already stopped.")
    except libvirt.libvirtError as e:
        print(f"Error stopping VM {vm_name}: {str(e)}")


# Function to stop all VMs
def stop_all_vms(conn, base_name, num_vms):
    """Stop all VMs that were created."""
    for i in range(1, num_vms + 1):
        vm_name = f"{base_name}_{i}"
        stop_vm(conn, vm_name)

#Performance monitoring code
def get_vm_stats(conn, vm_name):
    try:
        domain = conn.lookupByName(vm_name)
        if not domain.isActive():
            print(f"VM {vm_name} is not running")
            return

        # Get CPU stats
        cpu_stats = domain.getCPUStats(True)
        cpu_time = cpu_stats[0]['cpu_time'] / 1e9  # Convert from nanoseconds to seconds

        # Get memory stats
        mem_stats = domain.memoryStats()
        memory_used = mem_stats.get('rss', 0) / 1024  # Convert to MB

        # Fetch the network interface information
        interfaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)

        if not interfaces:
            print(f"No interfaces found via agent, falling back to LEASE method.")
            interfaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0)

        print(f"Interfaces found for VM {vm_name}: {interfaces.keys()}")

        if not interfaces:
            print(f"No network interfaces found for VM {vm_name}.")
            return

        for iface_name, iface_info in interfaces.items():
            # Skip loopback and invalid interfaces
            if iface_name == 'lo' or not iface_info:
                continue

            print(f"Checking stats for interface: {iface_name}")

            try:
                # Get the stats for valid interfaces
                iface_stats = domain.interfaceStats('vnet0')
                rx_bytes = iface_stats[0] / (1024 * 1024)  # Convert to MB
                tx_bytes = iface_stats[4] / (1024 * 1024)

                print(f"VM: {vm_name}")
                print(f"CPU time used: {cpu_time:.2f} seconds")
                print(f"Memory used: {memory_used:.2f} MB")
                print(f"Network ({iface_name}) RX: {rx_bytes:.2f} MB, TX: {tx_bytes:.2f} MB\n")

            except libvirt.libvirtError as e:
                print(f"Error getting stats for interface {iface_name}: {str(e)}")

    except libvirt.libvirtError as e:
        print(f"Error getting stats for VM {vm_name}: {str(e)}")



# Main program
def main():
    conn = connect_to_hypervisor()

    # Multiple VMs
    #base_name = "UbuntuServervm"
    #num_vms = 1  # Number of VMs to create
    #base_disk = "/home/oliver/VMs/UbuntuServer.qcow2"  # Path to the base disk
    #iso_image = "/home/oliver/VMs/UbuntuServerIso.iso"  # Path to the ISO image

    # Create multiple VMs
    #create_multiple_vms(conn, base_name, num_vms, base_disk, iso_image)

    # Start all the VMs
    #start_all_vms(conn, base_name, num_vms)

    # Stop all the VMs
    #stop_all_vms(conn, base_name, num_vms)
    vm_names = ["UbuntuBaseVM"] #, "UbuntuServervm_2", "UbuntuServervm_3"]
    # Monitor performance in a loop
    while True:
        for vm_name in vm_names:
            get_vm_stats(conn, vm_name)
        time.sleep(5)  # Check every 5 seconds
    # Close the connection
    #conn.close()


if __name__ == "__main__":
    main()
