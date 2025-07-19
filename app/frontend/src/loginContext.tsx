/**
 * This file defines a context for managing login state in a React application.
 * Context provides a way to pass data through the component tree without having to pass props down manually at every level.
 * For more information, refer to the official React documentation:
 * https://react.dev/learn/passing-data-deeply-with-context
 */

import { createContext } from "react";

export const LoginContext = createContext({
    loggedIn: false,
    setLoggedIn: (_: boolean) => {}
});
