from odoo import fields, models, api
from dateutil.relativedelta import relativedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate property"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(string='Available From', copy=False,
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
    active = fields.Boolean()
    state = fields.Selection(string="State", copy=False, default='New',
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

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids.price")
    def _compute_best_offer(self):
        for record in self:
            record.best_price = max(record.mapped("offer_ids").mapped("price"))

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden is True:
            self.garden_area = 10
            self.garden_orientation = "North"
        if self.garden is False:
            self.garden_area = 0
            self.garden_orientation = ""

class EstatePropertyTypes(models.Model):
    _name = "estate.property.types"
    _description = "Estate property type"

    name = fields.Char()

class EstatePropertyTags(models.Model):
    _name = "estate.property.tags"
    _description = "Estate property tags"

    name = fields.Char()

class EstatePropertyOffers(models.Model):
    _name = "estate.property.offers"
    _description = "Estate property offers"

    price = fields.Float()
    status = fields.Selection(copy=False, selection=[('Accepted', 'Accepted'), ('Refused', 'Refused')])
    partner_id = fields.Many2one(comodel_name="res.partner", string="Buyer", required=True)
    property_id = fields.Many2one(comodel_name="estate.property")

    create_date = fields.Date()
    validity = fields.Integer(default=7, string="Validity (days)")
    date_deadline = fields.Date(compute="_compute_date_deadline", inverse="_inverse_date_deadline", string="Deadline")

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
