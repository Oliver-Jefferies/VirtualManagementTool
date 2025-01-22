document.getElementById("startVmForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const vmName = document.getElementById("startVmName").value;

    try {
        const response = await fetch(`/start_vm/${vmName}`, { method: "POST" });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        alert(data.message);
    } catch (error) {
        console.error("Error starting VM:", error);
        alert("Failed to start VM. See console for details.");
    }
});

document.getElementById("stopVmForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const vmName = document.getElementById("stopVmName").value;

    try {
        const response = await fetch(`/stop_vm/${vmName}`, { method: "POST" });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        alert(data.message);
    } catch (error) {
        console.error("Error stopping VM:", error);
        alert("Failed to stop VM. See console for details.");
    }
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




