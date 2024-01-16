import { memo } from 'react';
import styles from './Chat.module.css';


interface VideoPlayerProperties {
    hidden: boolean;
}

const VideoPlayerContainer = memo<VideoPlayerProperties>(({ hidden }) => (
    <div hidden={hidden} className={styles.playerContainer}>
        <div id="playerElement" />
    </div>
));



export default VideoPlayerContainer;
