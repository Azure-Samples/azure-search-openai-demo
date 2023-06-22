import styles from "./Footer.module.css";

const Footer = () => {
    return (
        <footer className={styles.footer}>
            <div>
                <p>GADA-i © 2023 · Todos los derechos reservados</p>
            </div>
            <div>
                <ul>
                    <li>POLÍTICA DE PRIVACIDAD</li>
                    <li>AVISO LEGAL</li>
                    <li>POLÍTICA DE COOKIES</li>
                </ul>
            </div>
        </footer>
    );
};

export default Footer;
