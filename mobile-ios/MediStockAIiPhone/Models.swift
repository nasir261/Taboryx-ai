import Foundation

struct DashboardSummary {
    let currentStockValue: Double
    let lowStockCount: Int
    let expiredCount: Int
    let pendingOrders: Int
    let topUsedItems: [InventoryItem]
    let stockTrend: [TrendPoint]
}

struct TrendPoint: Identifiable, Hashable {
    let id = UUID()
    let date: String
    let value: Double
}

struct InventoryItem: Identifiable, Hashable, Codable {
    let id: Int
    let name: String
    let category: String
    let barcode: String
    let quantity: Int
    let minimumQuantity: Int
    let status: String
    let expiryDate: String?
}

struct MovementItem: Identifiable, Codable {
    let id: Int
    let itemName: String
    let movementType: String
    let quantity: Int
    let date: String
}

struct SessionInfo {
    var username: String = ""
    var role: String = ""
    var isLoggedIn: Bool = false
    var authToken: String?
}
