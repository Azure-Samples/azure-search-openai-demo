const { BlockBlobClient } = require("@azure/storage-blob");

const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-button");
const progress = document.getElementById("progress");

uploadButton.addEventListener("click", async () => {
    progress.innerText = "Uploading...";

    const file = fileInput.files[0];
    const blobName = file.name;
    const { sasUrl } = await fetch(`/sas?filename=${blobName}`).then((res) => res.json());

    const blobClient = new BlockBlobClient(sasUrl);
    await blobClient.uploadBrowserData(file);

    progress.innerText = "Uploaded! Starting job...";

    const jobInfo = await fetch(`/startjob?filename=${blobName}`, { method: "POST" })
        .then((res) => res.json());

    console.log(JSON.stringify(jobInfo, null, 2));

    const jobName = jobInfo.result?.name;
    if (jobName) {
        progress.innerText = `Job ${jobName} started. Waiting for output...`;
    }

    const logFileUrl = jobInfo.logFileUrl;
    let tries = 0;
    while(tries++ < 500) {
        const logFileResponse = await fetch(logFileUrl);
        if (logFileResponse.status === 200) {
            progress.innerText = await logFileResponse.text();
            window.scrollTo(0, document.body.scrollHeight);
            if (progress.innerText.match(/Indexed \d+ sections, \d+ succeeded/i)) {
                break;
            }
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
    }
});

