const { exec } = require("child_process");

function runCommand(userInput) {
    // ❌ SECURITY: Command Injection
    exec("ls " + userInput, (err, stdout) => {
        if (err) {
            console.error(err);
        }
        console.log(stdout);
    });
}

function calculateDiscount(price, isPremium) {
    // ❌ LOGIC: Wrong condition
    if (isPremium = true) {
        return price * 0.5;
    }
    return price;
}

function messyCallback(data) {
    // ❌ QUALITY: Deep nesting
    if (data) {
        if (data.user) {
            if (data.user.profile) {
                if (data.user.profile.settings) {
                    console.log("Very deep");
                }
            }
        }
    }
}

runCommand(process.argv[2]);
