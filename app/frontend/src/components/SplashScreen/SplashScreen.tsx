import styles from "./SplashScreen.module.css";
import { LoginButton } from "../../components/LoginButton";

interface SplashScreenProps {
    onLogin?: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onLogin }) => {
    return (
        <div className={styles.splashScreen}>
            <div className={styles.imageContainer}>
                <img
                src="https://staudiolydevaueast001.blob.core.windows.net/images-blob/splash_screen_svg.svg"
                    //src="/splash_screen_svg.svg"
                    alt="Splash Screen"
                    className={styles.splashImage}
                />
                {/* Text overlay */}
                <div className={styles.textOverlay}>
                    <LoginButton onLogin={onLogin} />
                </div>
            </div>
        </div>
    );
};
