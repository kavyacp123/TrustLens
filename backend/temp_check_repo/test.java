import java.sql.*;

public class VulnerableJava {

    // ❌ SECURITY: Hardcoded credentials
    private static final String DB_USER = "admin";
    private static final String DB_PASS = "password123";

    public static void getUser(String id) throws Exception {
        Connection conn = DriverManager.getConnection(
            "jdbc:mysql://localhost:3306/users", DB_USER, DB_PASS
        );

        Statement stmt = conn.createStatement();

        // ❌ SECURITY: SQL Injection
        String query = "SELECT * FROM users WHERE id = '" + id + "'";
        ResultSet rs = stmt.executeQuery(query);

        while (rs.next()) {
            System.out.println(rs.getString("name"));
        }

        // ❌ QUALITY: Resources never closed
    }

    public static int divide(int a, int b) {
        // ❌ LOGIC: No zero check
        return a / b;
    }
}
