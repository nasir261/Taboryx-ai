import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var model: AppViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    summaryCards
                    topUsedSection
                    trendSection
                }
                .padding()
            }
            .navigationTitle("Dashboard")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(AppConfiguration.appName).font(.title.bold())
            Text("Pharmacy inventory for iPhone").foregroundStyle(.secondary)
        }
    }

    private var summaryCards: some View {
        let dash = model.dashboard
        return VStack(spacing: 12) {
            HStack {
                StatCard(title: "Stock Value", value: dash.map { "£\(Int($0.currentStockValue))" } ?? "--")
                StatCard(title: "Low Stock", value: dash.map { "\($0.lowStockCount)" } ?? "--")
            }
            HStack {
                StatCard(title: "Expired", value: dash.map { "\($0.expiredCount)" } ?? "--")
                StatCard(title: "Pending POs", value: dash.map { "\($0.pendingOrders)" } ?? "--")
            }
        }
    }

    private var topUsedSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Top Used Items").font(.headline)
            ForEach(model.dashboard?.topUsedItems ?? [], id: \.self) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(item.name).font(.headline)
                        Text(item.category).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text("\(item.quantity)").font(.headline)
                }
                .padding()
                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14))
            }
        }
    }

    private var trendSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Stock Trend").font(.headline)
            if let points = model.dashboard?.stockTrend {
                HStack(alignment: .bottom, spacing: 8) {
                    ForEach(points) { point in
                        VStack {
                            RoundedRectangle(cornerRadius: 6)
                                .fill(Color.blue)
                                .frame(width: 18, height: CGFloat(max(20, point.value / 3000)))
                            Text(point.date).font(.caption2)
                        }
                    }
                }
                .frame(height: 160, alignment: .bottom)
            } else {
                Text("Loading trend...").foregroundStyle(.secondary)
            }
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.title2.bold())
        }
        .frame(maxWidth: .infinity, minHeight: 90, alignment: .leading)
        .padding()
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

