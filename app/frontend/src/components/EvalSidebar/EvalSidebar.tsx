import styles from "./EvalSidebar.module.css";

import { NavLink } from "react-router-dom";

const EvalSidebar = () => {
    return (
        <div className={styles.sidebar}>
            <h2>Evaluation</h2>
            <ul>
                <li>
                    <NavLink to="/eval" className={({ isActive }) => (isActive ? styles.sidebarLinkActive : styles.sidebarLink)}>
                        Home
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/eval_cases" className={({ isActive }) => (isActive ? styles.sidebarLinkActive : styles.sidebarLink)}>
                        Review Feedback
                    </NavLink>
                </li>
                <li>
                    <NavLink to="/eval_batch" className={({ isActive }) => (isActive ? styles.sidebarLinkActive : styles.sidebarLink)}>
                        Batch Evaluation
                    </NavLink>
                </li>
            </ul>
        </div>
    );
};
export default EvalSidebar;
