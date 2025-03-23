function fetchVMList() {
    fetch('/list_vms')
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                const vmListContainer = document.getElementById("vm-list");
                vmListContainer.innerHTML = ""; // Clear old list

                data.vms.forEach(vm => {
                    const row = document.createElement("tr");
                    row.innerHTML = `<td>${vm.name}</td><td>${vm.status === "on" ? "🟢 On" : "🔴 Off"}</td>`;
                    vmListContainer.appendChild(row);
                });
            }
        })
        .catch(error => console.error("Error fetching VM list:", error));
}

// Refresh VM list every 5 seconds
setInterval(fetchVMList, 5000);

// Fetch immediately when the page loads
document.addEventListener("DOMContentLoaded", fetchVMList);

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded and parsed");

    // Check if the form exists before adding event listeners
    const createVmForm = document.getElementById("createVmForm");
    if (!createVmForm) {
        console.error("Error: createVmForm not found!");
        return;
    }

    createVmForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const vmName = document.getElementById("createVmName").value.trim();
        const baseDisk = document.getElementById("createVmDisk").value.trim();
        const isoImage = document.getElementById("createVmIso").value.trim();
        const memory = parseInt(document.getElementById("createVmMemory").value);
        const cpus = parseInt(document.getElementById("createVmCores").value);
        const numVMs = parseInt(document.getElementById("numVMs").value) || 1;

        if (!vmName || !baseDisk || !isoImage || memory <= 0 || cpus <= 0 || numVMs <= 0) {
            alert("Please fill all fields correctly.");
            return;
        }

        let vmList = [];
        for (let i = 1; i <= numVMs; i++) {
            const generatedName = `${vmName}${i}`;
            const macAddress = `52:54:00:${Math.floor(Math.random() * 256).toString(16)}:${Math.floor(Math.random() * 256).toString(16)}:${Math.floor(Math.random() * 256).toString(16)}`;

            vmList.push({
                vm_name: generatedName,
                base_disk: baseDisk,
                iso_image: isoImage,
                memory: memory,
                cpus: cpus,
                mac_address: macAddress
            });
        }

        fetch('/create_vm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(numVMs === 1 ? vmList[0] : vmList),
        })
        .then(response => response.json())
        .then(data => {
            console.log("VM Creation Response:", data);
            alert("VMs created successfully!");
            fetchVMList();
        })
        .catch(error => console.error("Error creating VMs:", error));
    });

});

function deleteVM() {
    const vmName = document.getElementById("deleteVmName").value.trim();
    const isBulk = document.getElementById("deleteBulkCheckbox").checked;

    if (!vmName) {
        alert("Please enter a VM name or base name.");
        return;
    }

    const requestData = isBulk
        ? { base_name: vmName, bulk: true }
        : { vm_name: vmName, bulk: false };

    fetch('/delete_vm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            let message = isBulk
                ? `Deleted VMs: ${data.deleted_vms.join(", ")}`
                : data.message;
            alert(message);
            fetchVMList(); // Refresh VM list
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => console.error("Error deleting VM(s):", error));
}

document.getElementById("startVmForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent page reload

     const vmName = document.getElementById("startVmName").value.trim();
    const isBulk = document.getElementById("startBulkCheckbox").checked;

    if (!vmName) {
        alert("Please enter a VM name or base name.");
        return;
    }

    const requestData = isBulk
        ? { base_name: vmName, bulk: true }
        : { vm_name: vmName, bulk: false };

    fetch('/start_vm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            let message = isBulk
                ? `Started VMs: ${data.started_vms.join(", ")}`
                : data.message;
            alert(message);
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => console.error("Error starting VM(s):", error));
});


document.getElementById("stopVmForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent page reload

    const vmName = document.getElementById("stopVmName").value.trim();
    const isBulk = document.getElementById("stopBulkCheckbox").checked;

    if (!vmName) {
        alert("Please enter a VM name or base name.");
        return;
    }

    const requestData = isBulk
        ? { base_name: vmName, bulk: true }
        : { vm_name: vmName, bulk: false };

    fetch('/stop_vm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            let message = isBulk
                ? `Stopped VMs: ${data.stopped_vms.join(", ")}`
                : data.message;
            alert(message);
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => console.error("Error stopping VM(s):", error));
});

document.addEventListener("DOMContentLoaded", () => {
    const cpuChartCtx = document.getElementById("cpuUsageChart").getContext("2d");
    const memChartCtx = document.getElementById("memUsageChart").getContext("2d");
    const netChartCtx = document.getElementById("netUsageChart").getContext("2d");

    let netUsageChart;
    let memUsageChart;
    let cpuUsageChart;
    let updateInterval;

    // Initialize the graph
    function initializeGraph() {
        cpuUsageChart = new Chart(cpuChartCtx, {
            type: "line",
            data: {
                labels: [], // Time intervals
                datasets: [
                    {
                        label: "CPU Load (%)",
                        data: [],
                        backgroundColor: "rgba(75, 192, 192, 0.2)",
                        borderColor: "rgba(75, 192, 192, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Time",
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "CPU Load (%)",
                        },
                        beginAtZero: true,
                        max: 100,
                    },
                },
            },
        });


        memUsageChart = new Chart(memChartCtx, {
            type: "line",
            data: {
                labels: [], // Time intervals
                datasets: [
                    {
                        label: "RAM Usage (MB)",
                        data: [],
                        backgroundColor: "rgba(75, 192, 192, 0.2)",
                        borderColor: "rgba(75, 192, 192, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Time",
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Ram Usage (MB)",
                        },
                        beginAtZero: true,
                        max: 100,
                    },
                },
            },
        });

        netUsageChart = new Chart(netChartCtx, {
            type: "line",
            data: {
                labels: [], // Time intervals
                datasets: [
                    {
                        label: "Net Usage in",
                        data: [],
                        backgroundColor: "rgba(75, 192, 192, 0.2)",
                        borderColor: "rgba(75, 192, 192, 1)",
                        borderWidth: 1,
                    },
                    {
                        label: "Net Usage out",
                        data: [],
                        backgroundColor: "rgba(20, 50, 40, 0.2)",
                        borderColor: "rgba(75, 192, 192, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Time",
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Net Usage (MB)",
                        },
                        beginAtZero: true,
                        //max: 100,
                    },
                },
            },
        });
    }

    // Update the graph with new data
    function updateGraph(stats) {
        const currentTime = new Date().toLocaleTimeString();
        const cpuLoad = parseFloat(stats.cpu_load); // Extract CPU load percentage
        const memLoad = parseFloat(stats.memory_used); // Extract Memory usage percentage

        console.log(memLoad)


        if (isNaN(cpuLoad)) {
            console.error("Invalid CPU load value:", stats.cpu_load);
            return; // Prevent invalid data from being added
        }


        if (isNaN(memLoad)) {
            console.error("Invalid Memory usage value:", stats.cpu_load);
            return; // Prevent invalid data from being added
        }
        memUsageChart.options = {
            scales: {
                y: {
                    max: stats.memory_max
                }
            }
        }

        // Net data point
        netUsageChart.data.labels.push(currentTime);
        netUsageChart.data.datasets[0].data.push(stats.net_stats_in);
        netUsageChart.data.datasets[1].data.push(stats.net_stats_out)

        // Mem new data point
        memUsageChart.data.labels.push(currentTime);
        memUsageChart.data.datasets[0].data.push(memLoad);

        // Cpu new data point
        cpuUsageChart.data.labels.push(currentTime);
        cpuUsageChart.data.datasets[0].data.push(cpuLoad);

        // Limit the number of points on the graph
        if (cpuUsageChart.data.labels.length > 10) {
            cpuUsageChart.data.labels.shift();
            cpuUsageChart.data.datasets[0].data.shift();
        }

        if (memUsageChart.data.labels.length > 10) {
            memUsageChart.data.labels.shift();
            memUsageChart.data.datasets[0].data.shift();
        }

                // Limit the number of points on the graph
        if (netUsageChart.data.labels.length > 10) {
            netUsageChart.data.labels.shift();
            netUsageChart.data.datasets[0].data.shift();
            netUsageChart.data.datasets[1].data.shift();
        }

        // Update the chart
        cpuUsageChart.update();
        memUsageChart.update();
        netUsageChart.update();
    }

    // Fetch VM stats and update the graph periodically
    async function fetchAndUpdateGraph(vmName) {
        try {
            const response = await fetch(`/vm_stats/${vmName}`);
            if (!response.ok) {
                throw new Error(`Error fetching VM stats: ${response.statusText}`);
            }
            const data = await response.json();
            if (data.status === "success" && data.stats) {
                updateGraph(data.stats);
            }
            console.log("Received VM Stats:", data);

        } catch (error) {
            console.error("Error fetching VM stats for live graph:", error);
        }
    }

    // Start live graph updates
    function startLiveGraphUpdates(vmName) {
        // Clear any existing interval to avoid duplicates
        if (updateInterval) {
            clearInterval(updateInterval);
        }

        // Fetch stats every 5 seconds
        updateInterval = setInterval(() => fetchAndUpdateGraph(vmName), 5000);
    }

    // Initialize the graph on page load
    initializeGraph();

    // Add event listener for VM stats form
    document.getElementById("getVmStatsForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const vmName = document.getElementById("getVmStatsName").value;

        try {
            const response = await fetch(`/vm_stats/${vmName}`, { method: "GET" });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();

            if (data.status !== "success" || !data.stats) {
                alert(`Error: Unable to fetch stats for VM ${vmName}.`);
                return;
            }

            const { cpu_load, memory_used, vm_name, memory_max, net_stats_in, net_stats_out} = data.stats;

            // Display the VM stats
            document.getElementById("vmStatsDisplay").style.display = "block";
            document.getElementById("vmStatsOutput").textContent = `
                VM Name: ${vm_name}
                CPU Load: ${cpu_load}%
                Memory Used: ${memory_used} MB
                Memory Max: ${memory_max}
                Net In: ${net_stats_in}
                Net Out: ${net_stats_out}
            `;

            // Show the graph container and start live updates
            document.getElementById("graphContainer").style.display = "block";

            // Start periodic updates for the graph
            startLiveGraphUpdates(vmName);
        } catch (error) {
            console.error("Error fetching VM stats:", error);
            alert("Failed to fetch VM stats. See console for details.");
        }
    });
});




