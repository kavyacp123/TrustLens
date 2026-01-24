type User = {
    id: number;
    role?: string;
};

function isAuthorized(user: User): boolean {
    // ❌ LOGIC: role can be undefined
    if (user.role!.toLowerCase() === "admin") {
        return true;
    }
    return false;
}

function parseInput(input: any): number {
    // ❌ SECURITY / LOGIC: unsafe any usage
    return input.value * 10;
}

function complexFunction(a: number, b: number, c: number) {
    // ❌ QUALITY: High complexity
    if (a > 0) {
        if (b > 0) {
            if (c > 0) {
                if (a + b > c) {
                    if (a * b > c) {
                        console.log("Too complex");
                    }
                }
            }
        }
    }
}
