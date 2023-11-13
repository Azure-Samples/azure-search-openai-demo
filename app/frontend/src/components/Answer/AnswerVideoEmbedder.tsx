import styles from "./Answer.module.css";

export const transformYotubeUrlsToEmbdedded = (str: string, iframeWidth: number): string => {
  const urls = extractYoutubeUrls(str);
  const urlTransformations: Record<string, string> = {};
  urls.forEach((url) => {
      const id = extractYouTubeId(url);
      const height = iframeWidth * 9 / 16 // keep 16 x 9 ratio.
      urlTransformations[url] = `<div class="${styles.videoContainer}" style="width: ${iframeWidth}px; height: ${height}px" ><iframe src="https://www.youtube.com/embed/${id}" frameborder="0" allowfullscreen></iframe></div>`;
  });
  let transformedStr = str;
  for (const [url, transformation] of Object.entries(urlTransformations)) {
    transformedStr = transformedStr.replace(url, transformation);
  }
  return transformedStr;
};

const extractYoutubeUrls = (str: string): Set<string> => {
    const youtubeUrlRegex = /http:\/\/youtube\.com\/watch\?v=[\w-]{11}/g;
    const urls = new Set<string>();
    let match;
    while ((match = youtubeUrlRegex.exec(str)) !== null) {
        urls.add(match[0]);
    }
    return urls;
};

const extractYouTubeId = (url: string): string => {
    const parsedUrl = new URL(url);
    const videoID = parsedUrl.searchParams.get('v');
    return videoID ?? "";
}