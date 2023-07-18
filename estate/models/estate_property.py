from odoo import fields, models, api, exceptions
from dateutil.relativedelta import relativedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate property"
    _order = "id desc"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(string='Available From', copy=False, required=False,
                                    default=fields.Datetime.today()+relativedelta(months=+3))
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer(string='Living Area (sqm)')
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer(string='Garden Area (sqm)')
    garden_orientation = fields.Selection(string='Garden Orientation',
        selection = [('North','North'),('South','South'),('West','West'),('East','East')])
    active = fields.Boolean(default = True)
    state = fields.Selection(string="Status", copy=False, default='New',
                             selection=[('New', 'New'), ('Offer Received', 'Offer Received'),
                                        ('Offer Accepted', 'Offer Accepted'), ('Sold', 'Sold'),
                                        ('Cancelled', 'Cancelled')])

    # Relations
    property_type_id = fields.Many2one(comodel_name="estate.property.types", string="Property Type", required=True)
    user_id = fields.Many2one(comodel_name="res.users", string="Salesperson", default=lambda self: self.env.user)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Buyer", copy=False)
    tag_ids = fields.Many2many(comodel_name="estate.property.tags", string="Tags", required=True)
    offer_ids = fields.One2many(comodel_name="estate.property.offers", inverse_name="property_id", string="Offers")

    # Computed fields
    total_area = fields.Integer(compute="_compute_total_area", string="Total area (sqm)")
    best_price = fields.Float(compute="_compute_best_offer", string="Best Offer")

    # Actions
    sold_action = fields.Char()
    cancel_action = fields.Char()

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_offer(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.mapped("offer_ids").mapped("price"))
            else:
                record.best_price = 0

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden is True:
            self.garden_area = 10
            self.garden_orientation = "North"
        if self.garden is False:
            self.garden_area = 0
            self.garden_orientation = ""

    def action_sold(self):
        for record in self:
            if record.sold_action and record.state == "Cancelled":
                raise exceptions.UserError("Cancelled properties cannot be sold.")
            else:
                record.sold_action = "Sold"
                record.state = "Sold"
        return True

    def action_cancel(self):
        for record in self:
            if record.sold_action and record.state == "Sold":
                raise exceptions.UserError("Sold properties cannot be cancelled.")
            else:
                record.state = "Cancelled"
                record.cancel_action = "Cancelled"
        return True

    # Constaints
    _sql_constraints = [
        ('positive_expected_price', 'CHECK(expected_price >= 0)', 'Expected price cannot be lower than 0'),
        ('positive_selling_price', 'CHECK(selling_price >= 0)', 'Selling price cannot be lower than 0'),
        ('positive_offer_price', 'CHECK(offer_ids.price >= 0)', 'Offer price cannot be lower than 0')
    ]

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for record in self:
            if record.offer_ids:
                if record.selling_price < record.expected_price * 0.9:
                    raise exceptions.ValidationError("The selling price cannot be lower than 90% of the expected price")

    @api.ondelete(at_uninstall=False)
    def _delete_property(self):
        for record in self:
            if record.state != ("New","Cancelled"):
                raise exceptions.ValidationError("Only new or cancelled properties can be deleted.")

class EstatePropertyTypes(models.Model):
    _name = "estate.property.types"
    _description = "Estate property type"
    _order = "name"
    sequence = fields.Integer('Sequence', default=1)

    name = fields.Char()

    property_ids = fields.One2many(comodel_name="estate.property", inverse_name="property_type_id")
    offer_ids = fields.One2many(comodel_name="estate.property.offers", inverse_name="property_type_id")

    offer_count = fields.Integer(compute="_compute_offer_count", string="Offers")

    _sql_constraints = [
        ('unique_property_type', 'UNIQUE(name)', 'Property type name must be unique')
    ]

    @api.depends("offer_ids","property_ids")
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)

class EstatePropertyTags(models.Model):
    _name = "estate.property.tags"
    _description = "Estate property tags"
    _order = "name"

    name = fields.Char()
    color = fields.Integer()

    _sql_constraints = [
        ('unique_property_tag', 'UNIQUE(name)', 'Property tag name must be unique')
    ]

class EstatePropertyOffers(models.Model):
    _name = "estate.property.offers"
    _description = "Estate property offers"
    _order = "price desc"

    price = fields.Float()
    status = fields.Selection(copy=False, selection=[('Accepted', 'Accepted'), ('Refused', 'Refused')])
    partner_id = fields.Many2one(comodel_name="res.partner", string="Buyer", required=True)
    property_id = fields.Many2one(comodel_name="estate.property")
    property_type_id =fields.Many2one(related="property_id.property_type_id")

    create_date = fields.Date()
    validity = fields.Integer(default=7, string="Validity (days)")
    date_deadline = fields.Date(compute="_compute_date_deadline", inverse="_inverse_date_deadline", string="Deadline")

    _sql_constraints = [
        ('positive_offer_price', 'CHECK(price >= 0)', 'Offer price cannot be lower than 0')
    ]

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for record in self:
            # create_date is False when adding a new line, so we need to set the date for today or we'll have an Error
            if record.create_date is False:
                record.create_date = fields.Datetime.today()
            record.date_deadline = record.create_date + relativedelta(days=record.validity)

    @api.depends("create_date","validity")
    def _inverse_date_deadline(self):
        for record in self:
            record.validity = (record.date_deadline - record.create_date).days

    def action_accept(self):
        for record in self:
            record.status = "Accepted"
            record.property_id.write({"selling_price":record.price, "partner_id":record.partner_id, "state":"Offer Accepted"})
            record.property_id.offer_ids.filtered(lambda x: x.status is False).status = "Refused"
        return True

    def action_refuse(self):
        for record in self:
            record.status = "Refused"
        return True

    @api.model
    def create(self, vals):
        property_id = self.env['estate_property'].browse(vals['property_id'])
        property_id.status = "Offer Received"
        self._check_new_offer()
        return super().create(vals)

    @api.constrains("price")
    def _check_new_offer(self):
        for record in self:
            if record.price < record.property_id.best_price:
                raise exceptions.UserError("Can't create an offer with a lower amount than an existing offer.")

class Users(models.Model):
    _inherit = "res.users"

    property_ids = fields.One2many(comodel_name="estate.property", inverse_name="user_id")
