#include <Arduino.h>
#include <esp_arduino_version.h>

#define TB_PWMA_PIN  21
#define TB_AIN2_PIN  47
#define TB_AIN1_PIN  48
#define TB_STBY_PIN  39
#define TB_BIN1_PIN  40
#define TB_BIN2_PIN  41
#define TB_PWMB_PIN  42

#define ECHO_PIN   4
#define TRIG_PIN   5
#define SERVO_PIN  7

static constexpr int LEFT_FORWARD_PWM = 46;
static constexpr int RIGHT_FORWARD_PWM = 54;
static constexpr int LEFT_REVERSE_PWM = 34;
static constexpr int RIGHT_REVERSE_PWM = 50;
static constexpr int LEFT_TURN_PWM = 42;
static constexpr int RIGHT_TURN_PWM = 56;
static constexpr int MOTOR_RAMP_STEP = 2;
static constexpr uint32_t MOTOR_RAMP_DELAY_MS = 20;
static constexpr int RIGHT_MOTOR_SIGN = -1;
static constexpr float OBSTACLE_DISTANCE_CM = 30.0f;
static constexpr uint32_t REVERSE_TIME_MS = 220;
static constexpr uint32_t TURN_TIME_MS = 380;
static constexpr uint32_t SERVO_SETTLE_MS = 250;
static constexpr uint32_t SERVO_STEP_DELAY_MS = 15;

static constexpr int SERVO_CENTER_DEG = 90;
static constexpr int SERVO_LEFT_DEG = 150;
static constexpr int SERVO_RIGHT_DEG = 30;

static constexpr uint32_t MOTOR_PWM_FREQ = 20000;
static constexpr uint8_t MOTOR_PWM_BITS = 8;
static constexpr uint32_t SERVO_PWM_FREQ = 50;
static constexpr uint8_t SERVO_PWM_BITS = 14;

#if ESP_ARDUINO_VERSION_MAJOR < 3
static constexpr uint8_t PWM_CHANNEL_LEFT = 0;
static constexpr uint8_t PWM_CHANNEL_RIGHT = 1;
static constexpr uint8_t PWM_CHANNEL_SERVO = 2;
#endif

static int currentLeftPwm = 0;
static int currentRightPwm = 0;
static int currentServoAngle = SERVO_CENTER_DEG;

static void writeLeftPwm(uint8_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(TB_PWMA_PIN, duty);
#else
    ledcWrite(PWM_CHANNEL_LEFT, duty);
#endif
}

static void writeRightPwm(uint8_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(TB_PWMB_PIN, duty);
#else
    ledcWrite(PWM_CHANNEL_RIGHT, duty);
#endif
}

static void writeServoPwm(uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(SERVO_PIN, duty);
#else
    ledcWrite(PWM_CHANNEL_SERVO, duty);
#endif
}

static void setLeftMotor(int pwm) {
    pwm = constrain(pwm, -255, 255);
    if (pwm > 0) {
        digitalWrite(TB_AIN1_PIN, HIGH);
        digitalWrite(TB_AIN2_PIN, LOW);
        writeLeftPwm((uint8_t)pwm);
    } else if (pwm < 0) {
        digitalWrite(TB_AIN1_PIN, LOW);
        digitalWrite(TB_AIN2_PIN, HIGH);
        writeLeftPwm((uint8_t)(-pwm));
    } else {
        digitalWrite(TB_AIN1_PIN, LOW);
        digitalWrite(TB_AIN2_PIN, LOW);
        writeLeftPwm(0);
    }
}

static void setRightMotor(int pwm) {
    pwm *= RIGHT_MOTOR_SIGN;
    pwm = constrain(pwm, -255, 255);
    if (pwm > 0) {
        digitalWrite(TB_BIN1_PIN, HIGH);
        digitalWrite(TB_BIN2_PIN, LOW);
        writeRightPwm((uint8_t)pwm);
    } else if (pwm < 0) {
        digitalWrite(TB_BIN1_PIN, LOW);
        digitalWrite(TB_BIN2_PIN, HIGH);
        writeRightPwm((uint8_t)(-pwm));
    } else {
        digitalWrite(TB_BIN1_PIN, LOW);
        digitalWrite(TB_BIN2_PIN, LOW);
        writeRightPwm(0);
    }
}

static int stepToward(int current, int target, int step) {
    if (current < target) return min(current + step, target);
    if (current > target) return max(current - step, target);
    return current;
}

static void moveMotorsSlow(int leftTarget, int rightTarget) {
    while (currentLeftPwm != leftTarget || currentRightPwm != rightTarget) {
        currentLeftPwm = stepToward(currentLeftPwm, leftTarget, MOTOR_RAMP_STEP);
        currentRightPwm = stepToward(currentRightPwm, rightTarget, MOTOR_RAMP_STEP);
        setLeftMotor(currentLeftPwm);
        setRightMotor(currentRightPwm);
        delay(MOTOR_RAMP_DELAY_MS);
    }
}

static void stopCar() {
    moveMotorsSlow(0, 0);
}

static void forward() {
    moveMotorsSlow(LEFT_FORWARD_PWM, RIGHT_FORWARD_PWM);
}

static void backward() {
    moveMotorsSlow(-LEFT_REVERSE_PWM, -RIGHT_REVERSE_PWM);
}

static void turnLeft() {

    moveMotorsSlow(0, RIGHT_TURN_PWM);
}

static void turnRight() {

    moveMotorsSlow(LEFT_TURN_PWM, 0);
}

static void servoWriteRaw(int angleDeg) {
    angleDeg = constrain(angleDeg, 0, 180);

    const uint32_t pulseUs = 500UL + (uint32_t)angleDeg * 2000UL / 180UL;
    const uint32_t servoMaxDuty = (1UL << SERVO_PWM_BITS) - 1UL;
    const uint32_t duty = pulseUs * servoMaxDuty / 20000UL;
    writeServoPwm(duty);
}

static void servoMoveSlow(int targetAngle) {
    targetAngle = constrain(targetAngle, 0, 180);
    while (currentServoAngle != targetAngle) {
        currentServoAngle += targetAngle > currentServoAngle ? 1 : -1;
        servoWriteRaw(currentServoAngle);
        delay(SERVO_STEP_DELAY_MS);
    }
}

static float readDistanceCm() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    const uint32_t durationUs = pulseIn(ECHO_PIN, HIGH, 30000UL);
    if (durationUs == 0) return 400.0f;

    const float distanceCm = (float)durationUs * 0.0343f * 0.5f;
    if (distanceCm < 2.0f || distanceCm > 400.0f) return 400.0f;
    return distanceCm;
}

static float lookAndMeasure(int servoAngle) {
    servoMoveSlow(servoAngle);
    delay(SERVO_SETTLE_MS);

    const float first = readDistanceCm();
    delay(40);
    const float second = readDistanceCm();
    const bool firstValid = first < 399.0f;
    const bool secondValid = second < 399.0f;
    if (firstValid && secondValid) return 0.5f * (first + second);
    if (firstValid) return first;
    if (secondValid) return second;
    return 400.0f;
}

static void avoidObstacle() {
    stopCar();
    delay(150);

    const float leftCm = lookAndMeasure(SERVO_LEFT_DEG);
    const float rightCm = lookAndMeasure(SERVO_RIGHT_DEG);

    servoMoveSlow(SERVO_CENTER_DEG);
    delay(200);

    Serial.printf("# SCAN left=%.1fcm right=%.1fcm\n", leftCm, rightCm);

    backward();
    delay(REVERSE_TIME_MS);
    stopCar();
    delay(120);

    if (leftCm >= rightCm) {
        Serial.println("# TURN LEFT");
        turnLeft();
    } else {
        Serial.println("# TURN RIGHT");
        turnRight();
    }

    delay(TURN_TIME_MS);
    stopCar();
    delay(120);

    servoMoveSlow(SERVO_CENTER_DEG);
    forward();
}

void setup() {
    Serial.begin(115200);

    pinMode(TB_AIN1_PIN, OUTPUT);
    pinMode(TB_AIN2_PIN, OUTPUT);
    pinMode(TB_BIN1_PIN, OUTPUT);
    pinMode(TB_BIN2_PIN, OUTPUT);
    pinMode(TB_STBY_PIN, OUTPUT);
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(TB_PWMA_PIN, MOTOR_PWM_FREQ, MOTOR_PWM_BITS);
    ledcAttach(TB_PWMB_PIN, MOTOR_PWM_FREQ, MOTOR_PWM_BITS);
    ledcAttach(SERVO_PIN, SERVO_PWM_FREQ, SERVO_PWM_BITS);
#else
    ledcSetup(PWM_CHANNEL_LEFT, MOTOR_PWM_FREQ, MOTOR_PWM_BITS);
    ledcSetup(PWM_CHANNEL_RIGHT, MOTOR_PWM_FREQ, MOTOR_PWM_BITS);
    ledcSetup(PWM_CHANNEL_SERVO, SERVO_PWM_FREQ, SERVO_PWM_BITS);
    ledcAttachPin(TB_PWMA_PIN, PWM_CHANNEL_LEFT);
    ledcAttachPin(TB_PWMB_PIN, PWM_CHANNEL_RIGHT);
    ledcAttachPin(SERVO_PIN, PWM_CHANNEL_SERVO);
#endif

    digitalWrite(TB_STBY_PIN, HIGH);
    digitalWrite(TRIG_PIN, LOW);
    stopCar();

    servoWriteRaw(SERVO_CENTER_DEG);
    currentServoAngle = SERVO_CENTER_DEG;
    delay(800);

    Serial.println("# READY - SLOW AUTO FORWARD");
    forward();
}

void loop() {
    const float frontCm = readDistanceCm();

    static uint32_t lastPrintMs = 0;
    if ((uint32_t)(millis() - lastPrintMs) >= 500) {
        lastPrintMs = millis();
        Serial.printf("# FRONT %.1fcm\n", frontCm);
    }

    if (frontCm <= OBSTACLE_DISTANCE_CM) {
        Serial.println("# OBSTACLE - STOP AND SCAN");
        avoidObstacle();
    } else {
        forward();
    }

    delay(80);
}
