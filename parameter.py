class ProblemSolver:
    def __init__(self, problem_name):
        self.problem_name = problem_name
        self.steps = []
        self.variables = {}
        self.equations = {}
        self.conditions = {}
        self.verification_points = []
        
    def log_step(self, step_name, description, calculation=None, result=None):
        """Log each step with full observability"""
        step = {
            'number': len(self.steps) + 1,
            'name': step_name,
            'description': description,
            'calculation': calculation,
            'result': result
        }
        self.steps.append(step)
        print(f"\n{'='*60}")
        print(f"STEP {step['number']}: {step_name}")
        print(f"{'='*60}")
        print(f"Description: {description}")
        if calculation:
            print(f"Calculation: {calculation}")
        if result is not None:
            print(f"Result: {result}")
        return result
    
    def define_variable(self, var_name, expression, value=None):
        """Define and track variables"""
        self.variables[var_name] = {
            'expression': expression,
            'value': value
        }
        print(f"\n[VARIABLE DEFINED] {var_name} = {expression}")
        if value is not None:
            print(f"                   {var_name} = {value}")
        return value
    
    def add_equation(self, eq_name, equation, simplified=None):
        """Add and track equations"""
        self.equations[eq_name] = {
            'original': equation,
            'simplified': simplified or equation
        }
        print(f"\n[EQUATION {eq_name}] {equation}")
        if simplified and simplified != equation:
            print(f"                    Simplified: {simplified}")
    
    def add_condition(self, cond_name, condition, implication):
        """Add problem conditions"""
        self.conditions[cond_name] = {
            'condition': condition,
            'implication': implication
        }
        print(f"\n[CONDITION] {cond_name}: {condition}")
        print(f"            Implies: {implication}")
    
    def verify(self, check_name, left, right, operator="="):
        """Verify calculations"""
        operators = {
            "=": lambda l, r: abs(l - r) < 0.0001,
            "!=": lambda l, r: abs(l - r) >= 0.0001,
            ">": lambda l, r: l > r,
            "<": lambda l, r: l < r,
            ">=": lambda l, r: l >= r,
            "<=": lambda l, r: l <= r
        }
        
        result = operators[operator](left, right)
        status = "✓ PASS" if result else "✗ FAIL"
        
        verification = {
            'name': check_name,
            'left': left,
            'right': right,
            'operator': operator,
            'result': result
        }
        self.verification_points.append(verification)
        
        print(f"\n[VERIFICATION] {check_name}")
        print(f"               {left} {operator} {right}")
        print(f"               Status: {status}")
        return result
    
    def solve_linear(self, eq1, eq2, var1, var2):
        """Solve system of linear equations"""
        print(f"\n[SOLVING SYSTEM]")
        print(f"Equation 1: {eq1}")
        print(f"Equation 2: {eq2}")
        print(f"Variables: {var1}, {var2}")
        # This is a placeholder - implement actual solving logic
        return None, None
    
    def compare_quantities(self, qty1_name, qty1_value, qty2_name, qty2_value):
        """Compare two quantities"""
        print(f"\n{'='*60}")
        print(f"QUANTITY COMPARISON")
        print(f"{'='*60}")
        print(f"{qty1_name} = {qty1_value}")
        print(f"{qty2_name} = {qty2_value}")
        
        if qty1_value > qty2_value:
            relation = f"{qty1_name} > {qty2_name}"
        elif qty1_value < qty2_value:
            relation = f"{qty1_name} < {qty2_name}"
        else:
            relation = f"{qty1_name} = {qty2_name}"
        
        print(f"\nRelation: {relation}")
        return relation
    
    def check_options(self, options, z_val, y_val):
        """Check which option satisfies the relationship"""
        print(f"\n{'='*60}")
        print(f"CHECKING OPTIONS")
        print(f"{'='*60}")
        print(f"Given: z = {z_val}, y = {y_val}\n")
        
        results = {}
        for opt_num, opt_expr in options.items():
            try:
                # Evaluate the option
                left, right = opt_expr.split('=')
                left_val = eval(left.strip(), {'z': z_val, 'y': y_val})
                right_val = eval(right.strip(), {'z': z_val, 'y': y_val})
                
                match = abs(left_val - right_val) < 0.0001
                results[opt_num] = match
                
                status = "✓" if match else "✗"
                print(f"Option {opt_num}: {opt_expr}")
                print(f"            {left_val} = {right_val} {status}")
                print()
            except Exception as e:
                print(f"Option {opt_num}: Error - {e}\n")
                results[opt_num] = False
        
        return results
    
