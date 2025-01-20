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

        const { cpu_time, memory_used, vm_name } = data.stats;

        document.getElementById("vmStatsDisplay").style.display = "block";
        document.getElementById("vmStatsOutput").textContent = `
            VM Name: ${vm_name}
            CPU Time Used: ${cpu_time}
            Memory Used: ${memory_used}
        `;
    } catch (error) {
        console.error("Error fetching VM stats:", error);
        alert("Failed to fetch VM stats. See console for details.");
    }
});
