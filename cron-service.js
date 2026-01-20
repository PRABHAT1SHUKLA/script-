const cron = require('node-cron');
const { Student, Payment, NotificationLog } = require('../models');
const { Op } = require('sequelize');
const { sendPaymentReminder } = require('./notificationService');

// Check and send notifications
async function checkAndSendNotifications() {
  console.log('Running payment notification check...');

  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Calculate target dates
    const sevenDaysFromNow = new Date(today);
    sevenDaysFromNow.setDate(sevenDaysFromNow.getDate() + 7);

    const fifteenDaysFromNow = new Date(today);
    fifteenDaysFromNow.setDate(fifteenDaysFromNow.getDate() + 15);

    // Find payments due in 7 days
    const paymentsIn7Days = await Payment.findAll({
      where: {
        status: 'pending',
        due_date: {
          [Op.gte]: sevenDaysFromNow,
          [Op.lt]: new Date(sevenDaysFromNow.getTime() + 24 * 60 * 60 * 1000)
        }
      },
      include: [{ model: Student }]
    });

    // Find payments due in 15 days
    const paymentsIn15Days = await Payment.findAll({
      where: {
        status: 'pending',
        due_date: {
          [Op.gte]: fifteenDaysFromNow,
          [Op.lt]: new Date(fifteenDaysFromNow.getTime() + 24 * 60 * 60 * 1000)
        }
      },
      include: [{ model: Student }]
    });

    // Find overdue payments
    const overduePayments = await Payment.findAll({
      where: {
        status: { [Op.in]: ['pending', 'overdue'] },
        due_date: { [Op.lt]: today }
      },
      include: [{ model: Student }]
    });

    // Update overdue payment statuses
    if (overduePayments.length > 0) {
      await Payment.update(
        { status: 'overdue' },
        {
          where: {
            id: { [Op.in]: overduePayments.map(p => p.id) }
          }
        }
      );
    }

    // Send notifications for 15-day reminders
    for (const payment of paymentsIn15Days) {
      // Check if notification already sent today
      const alreadySent = await NotificationLog.findOne({
        where: {
          payment_id: payment.id,
          days_before: 15,
          status: 'sent',
          sent_at: { [Op.gte]: today }
        }
      });

      if (!alreadySent) {
        await sendPaymentReminder(payment.Student, payment, 15);
        console.log(`Sent 15-day reminder to ${payment.Student.name}`);
      }
    }

    // Send notifications for 7-day reminders
    for (const payment of paymentsIn7Days) {
      const alreadySent = await NotificationLog.findOne({
        where: {
          payment_id: payment.id,
          days_before: 7,
          status: 'sent',
          sent_at: { [Op.gte]: today }
        }
      });

      if (!alreadySent) {
        await sendPaymentReminder(payment.Student, payment, 7);
        console.log(`Sent 7-day reminder to ${payment.Student.name}`);
      }
    }

    // Send overdue notifications
    for (const payment of overduePayments) {
      const daysOverdue = Math.floor((today - payment.due_date) / (1000 * 60 * 60 * 24));
      
      const alreadySent = await NotificationLog.findOne({
        where: {
          payment_id: payment.id,
          days_before: -daysOverdue,
          status: 'sent',
          sent_at: { [Op.gte]: today }
        }
      });

      if (!alreadySent) {
        await sendPaymentReminder(payment.Student, payment, -daysOverdue);
        console.log(`Sent overdue notice to ${payment.Student.name} (${daysOverdue} days overdue)`);
      }
    }

    console.log(`Notification check completed. 
      15-day reminders: ${paymentsIn15Days.length}
      7-day reminders: ${paymentsIn7Days.length}
      Overdue notices: ${overduePayments.length}`);

  } catch (error) {
    console.error('Notification cron error:', error);
  }
}

// Initialize cron job
function initializeCronJobs() {
  // Run every day at 9 AM (0 9 * * *)
  // For testing, use '*/5 * * * *' to run every
