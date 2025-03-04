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
                    src="/splash_screen_svg.svg"
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
