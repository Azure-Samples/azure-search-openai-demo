import { Navigate, Outlet } from "react-router-dom";

export const consentStorageKey = "philConsentAccepted";

const ConsentGuard = () => {
    const hasConsent = localStorage.getItem(consentStorageKey) === "true";

    if (!hasConsent) {
        return <Navigate to="/" replace />;
    }

    return <Outlet />;
};

export default ConsentGuard;
