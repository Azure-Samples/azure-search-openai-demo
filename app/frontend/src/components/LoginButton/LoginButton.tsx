import { DefaultButton } from '@fluentui/react';

import styles from "./LoginButton.module.css";

export const LoginButton = () => {
  return (
    <DefaultButton text="Login" className={styles.loginButton} />
  );
};
