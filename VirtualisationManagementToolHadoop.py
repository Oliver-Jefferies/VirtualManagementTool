import libvirt
import os
import sys
import paramiko
import time


# Connect to the system's hypervisor
def connect_to_hypervisor():
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)
    return conn


# Function to read the XML from an external file or return a default XML if the file is not found
def load_xml_from_file(xml_file_path):
    # Base XML configuration with console setup
    base_xml = """<domain type='kvm'>
      <name>VM_NAME</name>
      <memory unit='KiB'>1048576</memory>
      <vcpu placement='static'>1</vcpu>
      <os>
        <type arch='x86_64' machine='pc-i440fx-2.9'>hvm</type>
        <boot dev='hd'/>
      </os>
      <disk type='file' device='disk'>
        <driver name='qemu' type='qcow2'/>
        <source file='DISK_IMAGE_PATH'/>
        <target dev='vda' bus='virtio'/>
        <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
      </disk>
      <interface type='network'>
        <mac address='52:54:00:xx:xx:xx'/>
        <source network='default'/>
        <model type='virtio'/>
        <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
      </interface>
      <serial type='dev'>
        <source path='/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AH01M9Y4-if00-port0'/>
        <target port='serial0'/>
      </serial>
      <console type='pty'>
        <source path='/dev/pts/0'/>
        <target type='serial' port='serial0'/>
      </console>
      <cloud-init>
        <user-data type='text/cloud-config'>#cloud-config
        users:
          - name: USERNAME_PLACEHOLDER
            passwd: PASSWORD_PLACEHOLDER  # Password can be hashed for production
            lock_passwd: false
            sudo: ['ALL=(ALL) NOPASSWD:ALL']
            groups: users, sudo
        ssh_pwauth: true
        package_update: true
        packages:
          - openjdk-11-jdk  # Install Java
        </user-data>
      </cloud-init>
    </domain>"""

    try:
        with open(xml_file_path, 'r') as xml_file:
            xml_config = xml_file.read()
        return xml_config
    except FileNotFoundError:
        print(f"Error: XML file {xml_file_path} not found. Using default XML.")
        return base_xml  # Return the base XML if the file is not found


# Function to create multiple VMs from the same base disk and XML template
def create_multiple_vms(conn, base_name, num_vms, base_disk, xml_template):
    vm_names = []
    for i in range(1, num_vms + 1):
        vm_name = f"{base_name}_{i}"
        vm_disk = f"/home/oliver/VMs/{vm_name}.qcow2"
        static_ip = f"192.168.122.{10 + i}"  # Assign static IPs

        # Ensure qemu-img command specifies the backing format
        os.system(f"qemu-img create -f qcow2 -o backing_file={base_disk},backing_fmt=qcow2 {vm_disk} 20G")

        # Load and update XML configuration for each VM
        xml_config = load_xml_from_file(xml_template)

        # Replace placeholders in the XML template
        username = f"user{i}"
        password = f"password{i}"  # You may want to hash passwords in production
        xml_config = xml_config.replace("DISK_IMAGE_PATH", vm_disk)
        xml_config = xml_config.replace("VM_NAME", vm_name)
        xml_config = xml_config.replace("USERNAME_PLACEHOLDER", username)
        xml_config = xml_config.replace("PASSWORD_PLACEHOLDER", password)  # Set plain password for cloud-init

        # Define and create the VM
        try:
            domain = conn.defineXML(xml_config)
            if domain is None:
                print(f"Error creating VM {vm_name} from XML.")
            else:
                vm_names.append(vm_name)
                print(f"VM {vm_name} created successfully.")
                # Start the VM after creation
                domain.create()
                print(f"VM {vm_name} started successfully.")
        except libvirt.libvirtError as e:
            print(f"Error defining VM {vm_name}: {e}")

    return vm_names


# Function to retry an operation
def retry_operation(func, *args, retries=5, delay=2):
    for attempt in range(retries):
        try:
            return func(*args)
        except Exception as e:
            print(f"Attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(delay)
    raise Exception(f"Operation failed after {retries} attempts")


# Function to install SSH on the VM using Paramiko
def install_ssh(static_ip, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(static_ip, username=username, password=password)
        print(f"SSH installed successfully on {static_ip}")
    except Exception as e:
        raise Exception(f"Failed to install SSH on {static_ip}: {e}")
    finally:
        ssh.close()


# Function to install Hadoop on the VM using Paramiko
def install_hadoop(static_ip, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(static_ip, username=username, password=password)

        # Install Hadoop using commands
        commands = [
            "wget https://downloads.apache.org/hadoop/common/hadoop-3.3.4/hadoop-3.3.4.tar.gz",
            "tar -xvzf hadoop-3.3.4.tar.gz",
            "sudo mv hadoop-3.3.4 /usr/local/hadoop",
            "echo 'export HADOOP_HOME=/usr/local/hadoop' >> ~/.bashrc",
            "echo 'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' >> ~/.bashrc",
            "source ~/.bashrc"
        ]

        for command in commands:
            stdin, stdout, stderr = ssh.exec_command(command)
            print(stdout.read().decode())
            print(stderr.read().decode())

        print(f"Hadoop installed successfully on {static_ip}")
    except Exception as e:
        raise Exception(f"Failed to install Hadoop on {static_ip}: {e}")
    finally:
        ssh.close()


# Main function to set up and run VMs
def main():
    conn = connect_to_hypervisor()

    base_name = "UbuntuServerVM"
    num_vms = 3  # Number of VMs to create
    base_disk = "/home/oliver/VMs/UbuntuServer.qcow2"  # Path to base disk image
    xml_template = "/home/oliver/VMs/XMLs/UbuntuServer.xml"  # Path to XML template

    # Create multiple VMs
    vm_names = create_multiple_vms(conn, base_name, num_vms, base_disk, xml_template)

    for vm_name in vm_names:
        static_ip = f"192.168.122.{10 + int(vm_name.split('_')[-1])}"
        username = f"user{vm_name.split('_')[-1]}"
        password = f"password{vm_name.split('_')[-1]}"

        # Retry SSH installation
        print(f"Installing SSH on {vm_name} at {static_ip}...")
        retry_operation(install_ssh, static_ip, username, password)

        # Retry Hadoop installation
        print(f"Installing Hadoop on {vm_name} at {static_ip}...")
        retry_operation(install_hadoop, static_ip, username, password)

    # Close the connection
    conn.close()


if __name__ == "__main__":
    main()
