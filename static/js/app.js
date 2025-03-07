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

document.getElementById("createVmForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent page reload

    const vmName = document.getElementById("createVmName").value;
    const baseDisk = document.getElementById("createVmDisk").value;
    const isoImage = document.getElementById("createVmIso").value;
    const memoryAllocate = document.getElementById("createVmMemory").value;
    const coresAllocate = document.getElementById("createVmCores").value;

    fetch('/create_vm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            vm_name: vmName,
            base_disk: baseDisk,
            iso_image: isoImage,
            memory_allocation: memoryAllocate,
            core_allocation: coresAllocate,
        }),
    })
    .then(response => response.json())
    .then(text => {
        console.log("Raw response:", text); // Log response for debugging
        return JSON.parse(text); // Now parse as JSON
    })
    .then(data => {
        alert(data.message);
        fetchVMList(); // Update the VM list
    })
    .catch(error => console.error("Error creating VM:", error));
});

document.getElementById("startVmForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent page reload

    const vmName = document.getElementById("startVmName").value.trim();

    fetch('/start_vm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vm_name: vmName }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message); // Show success/error message
        fetchVMList(); // Refresh VM list (if you added a function for this)
    })
    .catch(error => console.error("Error starting VM:", error));
});



document.getElementById("stopVmForm").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent page reload

    const vmName = document.getElementById("stopVmName").value.trim();
    if (!vmName) {
        alert("Please enter a VM name.");
        return;
    }

    fetch('/stop_vm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ vm_name: vmName }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message); // Show success/error message
        fetchVMList(); // Refresh VM list
    })
    .catch(error => console.error("Error stopping VM:", error));
});

document.addEventListener("DOMContentLoaded", () => {
    const cpuChartCtx = document.getElementById("cpuUsageChart").getContext("2d");
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
    }

    // Update the graph with new data
    function updateGraph(stats) {
        const currentTime = new Date().toLocaleTimeString();
        const cpuLoad = parseFloat(stats.cpu_load); // Extract CPU load percentage

        if (isNaN(cpuLoad)) {
            console.error("Invalid CPU load value:", stats.cpu_load);
            return; // Prevent invalid data from being added
        }

        // Add new data point
        cpuUsageChart.data.labels.push(currentTime);
        cpuUsageChart.data.datasets[0].data.push(cpuLoad);

        // Limit the number of points on the graph
        if (cpuUsageChart.data.labels.length > 10) {
            cpuUsageChart.data.labels.shift();
            cpuUsageChart.data.datasets[0].data.shift();
        }

        // Update the chart
        cpuUsageChart.update();
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

            const { cpu_load, memory_used, vm_name } = data.stats;

            // Display the VM stats
            document.getElementById("vmStatsDisplay").style.display = "block";
            document.getElementById("vmStatsOutput").textContent = `
                VM Name: ${vm_name}
                CPU Load: ${cpu_load}%
                Memory Used: ${memory_used} MB
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




