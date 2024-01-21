import { memo } from 'react';
import styles from './VideoPlayerContainer.module.css';


interface VideoPlayerProperties {
    hidden: boolean;
}

const VideoPlayerContainer = memo<VideoPlayerProperties>(({ hidden }) => (
    <div hidden={hidden} className={styles.wrapper}>
        <div id="playerElement" className={styles.player} />
    </div>
));



export default VideoPlayerContainer;
