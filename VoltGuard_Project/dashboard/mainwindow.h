/*
 * VoltGuard - Week 2: Native OT Dashboard (foundation)
 * -------------------------------------------------------
 * Per the project plan, Week 2's UI goal is just the FOUNDATION:
 *   "Build the foundation of a native Qt C++ desktop app to log
 *    incoming traffic."
 *
 * This window loads the bridge_report.jsonl file produced by
 * network_physics_bridge.py and displays every parsed command in a
 * table, color-flagging CATASTROPHIC verdicts.
 *
 * Real-time "predicted vs actual" graphs and dark-mode/rugged polish
 * are Week 3 / Week 4 items -- deliberately not built yet.
 */

#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QString>

QT_BEGIN_NAMESPACE
class QTableWidget;
class QLabel;
class QPushButton;
QT_END_NAMESPACE

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);

private slots:
    void onLoadReportClicked();

private:
    void loadReportFile(const QString& path);
    void setupUi();

    QTableWidget* trafficTable;
    QLabel*       statusLabel;
    QPushButton*  loadButton;
};

#endif // MAINWINDOW_H
