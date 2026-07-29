import Foundation

struct LoginResponse: Codable {
    let token: String
    let user: APIUser
}

struct APIUser: Codable {
    let id: Int?
    let username: String
    let email: String
    let fullName: String
    let role: String

    enum CodingKeys: String, CodingKey {
        case id, username, email, role
        case fullName = "full_name"
    }
}

struct TrendPointResponse: Codable {
    let date: String
    let value: Double
}

struct DashboardResponse: Codable {
    let currentStockValue: Double
    let lowStockCount: Int
    let expiredCount: Int
    let pendingOrders: Int
    let topUsedItems: [InventoryItem]
    let stockTrend: [TrendPointResponse]

    enum CodingKeys: String, CodingKey {
        case currentStockValue = "current_stock_value"
        case lowStockCount = "low_stock_count"
        case expiredCount = "expired_count"
        case pendingOrders = "pending_orders"
        case topUsedItems = "top_used_items"
        case stockTrend = "stock_trend"
    }
}

struct InventoryListResponse: Codable {
    let items: [InventoryItem]
}

struct MovementsResponse: Codable {
    let movements: [MovementItem]
}

struct ScanResponse: Codable {
    let found: Bool
    let code: String
    let message: String
    let item: InventoryItem?
}

final class APIClient {
    var baseURL: URL
    var authToken: String?

    init(baseURL: URL = AppConfiguration.defaultAPIBaseURL) {
        self.baseURL = baseURL
    }

    func login(username: String, password: String) async throws -> LoginResponse {
        let response: LoginResponse = try await request(
            path: "/auth/login",
            method: "POST",
            body: ["username": username, "password": password]
        )
        authToken = response.token
        return response
    }

    func fetchDashboardSummary() async throws -> DashboardSummary {
        let response: DashboardResponse = try await request(path: "/dashboard")
        return DashboardSummary(
            currentStockValue: response.currentStockValue,
            lowStockCount: response.lowStockCount,
            expiredCount: response.expiredCount,
            pendingOrders: response.pendingOrders,
            topUsedItems: response.topUsedItems,
            stockTrend: response.stockTrend.map { TrendPoint(date: $0.date, value: $0.value) }
        )
    }

    func fetchInventoryItems() async throws -> [InventoryItem] {
        let response: InventoryListResponse = try await request(path: "/inventory")
        return response.items
    }

    func fetchMovements() async throws -> [MovementItem] {
        let response: MovementsResponse = try await request(path: "/movements")
        return response.movements
    }

    func sendScan(code: String) async throws -> ScanResponse {
        try await request(path: "/scan", method: "POST", body: ["code": code])
    }

    private func request<T: Decodable>(path: String, method: String = "GET", body: [String: String]? = nil) async throws -> T {
        let cleanedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var url = baseURL
        for component in cleanedPath.split(separator: "/") {
            url.appendPathComponent(String(component))
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let authToken {
            request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        if httpResponse.statusCode >= 400 {
            let message = (try? JSONDecoder().decode(APIErrorResponse.self, from: data).error) ?? "Request failed"
            throw APIClientError.server(message)
        }
        let decoder = JSONDecoder()
        return try decoder.decode(T.self, from: data)
    }
}

struct APIErrorResponse: Codable {
    let error: String
}

enum APIClientError: LocalizedError {
    case server(String)

    var errorDescription: String? {
        switch self {
        case .server(let message):
            return message
        }
    }
}
