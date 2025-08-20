class CrossSessionValidator {
    constructor() {
        console.warn("[Stub] CrossSessionValidator loaded — no real validation logic.");
    }

    validateSession(session) {
        console.warn("[Stub] validateSession() called", session);
        return true; // Always passes
    }
}

module.exports = CrossSessionValidator;