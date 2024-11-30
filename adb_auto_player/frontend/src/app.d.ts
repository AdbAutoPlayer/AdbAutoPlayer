declare global {
    namespace App {
    }

    interface Window {
        // eel is injected at runtime by the eel package
        eel: any | undefined;
    }
}

export {};
