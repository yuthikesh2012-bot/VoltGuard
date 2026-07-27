#include "mainwindow.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QWidget>
#include <QTableWidget>
#include <QHeaderView>
#include <QLabel>
#include <QPushButton>
#include <QFileDialog>
#include <QFile>
#include <QTextStream>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QMessageBox>
#include <QColor>
#include <QFileInfo>

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    setupUi();
    setWindowTitle("VoltGuard OT Dashboard — Week 2 (foundation)");
    resize(900, 500);
}

void MainWindow::setupUi() {
    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);

    auto* topBar = new QHBoxLayout();
    loadButton = new QPushButton("Load Bridge Report...", central);
    statusLabel = new QLabel("No report loaded yet.", central);
    topBar->addWidget(loadButton);
    topBar->addWidget(statusLabel, 1);
    layout->addLayout(topBar);

    trafficTable = new QTableWidget(central);
    trafficTable->setColumnCount(7);
    trafficTable->setHorizontalHeaderLabels({
        "Frame", "Txn ID", "Function", "Register",
        "Value (RPM)", "Predicted PSI", "Verdict"
    });
    trafficTable->horizontalHeader()->setStretchLastSection(true);
    trafficTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    trafficTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    layout->addWidget(trafficTable);

    setCentralWidget(central);

    connect(loadButton, &QPushButton::clicked, this, &MainWindow::onLoadReportClicked);
}

void MainWindow::onLoadReportClicked() {
    QString path = QFileDialog::getOpenFileName(
        this, "Open bridge_report.jsonl", "../data", "JSON Lines (*.jsonl);;All files (*)");

    if (path.isEmpty()) return;
    loadReportFile(path);
}

void MainWindow::loadReportFile(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QMessageBox::warning(this, "Error", "Could not open file:\n" + path);
        return;
    }

    trafficTable->setRowCount(0);

    QTextStream in(&file);
    int row = 0;
    int catastrophicCount = 0;

    while (!in.atEnd()) {
        QString line = in.readLine().trimmed();
        if (line.isEmpty()) continue;

        QJsonParseError parseError;
        QJsonDocument doc = QJsonDocument::fromJson(line.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
            continue; // skip malformed lines rather than crash the dashboard
        }

        QJsonObject obj = doc.object();

        trafficTable->insertRow(row);

        auto setCell = [&](int col, const QString& text) {
            trafficTable->setItem(row, col, new QTableWidgetItem(text));
        };

        setCell(0, QString::number(obj.value("frame").toInt()));
        setCell(1, QString::number(obj.value("transaction_id").toInt()));
        setCell(2, QString("0x%1").arg(obj.value("function_code").toInt(), 2, 16, QChar('0')));
        setCell(3, obj.value("register_name").toString("-"));
        setCell(4, obj.contains("register_value")
                       ? QString::number(obj.value("register_value").toInt())
                       : "-");
        setCell(5, obj.contains("predicted_pressure_psi")
                       ? QString::number(obj.value("predicted_pressure_psi").toDouble())
                       : "-");

        QString verdict = obj.value("verdict").toString("-");
        setCell(6, verdict);

        if (verdict == "CATASTROPHIC") {
            catastrophicCount++;
            for (int col = 0; col < trafficTable->columnCount(); ++col) {
                if (auto* item = trafficTable->item(row, col)) {
                    item->setBackground(QColor(120, 20, 20));
                    item->setForeground(QColor(255, 220, 220));
                }
            }
        }

        row++;
    }

    statusLabel->setText(QString("Loaded %1 command(s) from %2 — %3 CATASTROPHIC")
                              .arg(row)
                              .arg(QFileInfo(path).fileName())
                              .arg(catastrophicCount));
}
