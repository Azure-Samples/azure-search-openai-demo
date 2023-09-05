const { BlockBlobClient } = require("@azure/storage-blob");

const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-button");

uploadButton.addEventListener("click", async () => {
    const file = fileInput.files[0];
    const blobName = file.name;
    const { sasUrl } = await fetch(`/sas?filename=${blobName}`).then((res) => res.json());

    const blobClient = new BlockBlobClient(sasUrl);
    await blobClient.uploadBrowserData(file);
});

